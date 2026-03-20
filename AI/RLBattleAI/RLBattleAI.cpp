/*
 * RLBattleAI.cpp, part of VCMI engine
 *
 * Authors: listed in file AUTHORS in main folder
 *
 * License: GNU General Public License v2.0 or later
 * Full text of license available in license.txt file, in main folder
 *
 */
#include "StdInc.h"
#include "RLBattleAI.h"

#include <boost/asio/ip/tcp.hpp>

#include "lib/ConditionalWait.h"
#include "lib/CThreadHelper.h"
#include "lib/CStack.h"
#include "lib/battle/BattleAction.h"
#include "lib/battle/BattleInfo.h"
#include "lib/bonuses/BonusSelector.h"
#include "lib/bonuses/Limiters.h"
#include "lib/battle/BattleLayout.h"
#include "lib/battle/CPlayerBattleCallback.h"
#include "lib/network/NetworkHandler.h"
#include "lib/networkPacks/PacksForClientBattle.h"
#include "callback/CBattleCallback.h"
#include "mapObjects/CGTownInstance.h"
#include "vcmi/Environment.h"


CRLBattleAI::CRLBattleAI()
	: side(BattleSide::NONE)
	, networkHandler(INetworkHandler::createHandler())
	, threadNetwork(&CRLBattleAI::threadRunNetwork, this)
	, actionReady(false)
	, wasWaitingForRealize(false)
	, wasUnlockingGs(false)
{
	std::string hostname = "127.0.0.1";
	uint16_t port = 65432;
	networkHandler->connectToRemote(*this, hostname, port);

	print("created");
}

CRLBattleAI::~CRLBattleAI()
{
	print("destroyed");
	networkHandler->stop();
	try
	{
		threadNetwork.join();
	}
	catch (const std::runtime_error & e)
	{
		logGlobal->error("Failed to shut down network thread! Reason: %s", e.what());
		assert(0);
	}

	if(cb)
	{
		//Restore previous state of CB - it may be shared with the main AI (like VCAI)
		cb->waitTillRealize = wasWaitingForRealize;
		cb->unlockGsWhenWaiting = wasUnlockingGs;
	}
}

void CRLBattleAI::threadRunNetwork()
{
	logGlobal->info("Starting network thread");
	setThreadName("runNetwork");
	try {
		networkHandler->run();
	}
	catch (const TerminationRequestedException &)
	{
		logGlobal->info("Terminating network thread");
		return;
	}
	logGlobal->info("Ending network thread");
}

void CRLBattleAI::initBattleInterface(std::shared_ptr<Environment> ENV, std::shared_ptr<CBattleCallback> CB)
{
	print("init called, saving ptr to IBattleCallback");
	env = ENV;
	cb = CB;

	wasWaitingForRealize = CB->waitTillRealize;
	wasUnlockingGs = CB->unlockGsWhenWaiting;
	CB->waitTillRealize = false;
	CB->unlockGsWhenWaiting = false;
}

void CRLBattleAI::initBattleInterface(std::shared_ptr<Environment> ENV, std::shared_ptr<CBattleCallback> CB, AutocombatPreferences autocombatPreferences)
{
	initBattleInterface(ENV, CB);
}

void CRLBattleAI::actionFinished(const BattleID & battleID, const BattleAction &action)
{
	print("actionFinished called");
}

void CRLBattleAI::actionStarted(const BattleID & battleID, const BattleAction &action)
{
	print("actionStarted called");
}

void CRLBattleAI::yourTacticPhase(const BattleID & battleID, int distance)
{
	cb->battleMakeTacticAction(battleID, BattleAction::makeEndOFTacticPhase(cb->getBattle(battleID)->battleGetTacticsSide()));
}

void CRLBattleAI::activeStack(const BattleID & battleID, const CStack * stack)
{
	//boost::this_thread::sleep_for(boost::chrono::seconds(2));
	print("activeStack called for " + stack->nodeName());

	// Send BattleSetActiveStack to Python server to request an action
	BattleSetActiveStack pack;
	pack.battleID = battleID;
	pack.stack = stack->unitId();
	pack.reason = BattleUnitTurnReason::TURN_QUEUE;
	
	print("Sending BattleSetActiveStack - battleID: " + std::to_string(battleID.getNum()) + 
	      ", stack: " + std::to_string(pack.stack));
	
	logicConnection->sendPack(pack);

	{
		std::unique_lock lk(actionMtx);
		actionCV.wait(lk, [this]{ return actionReady; });

		// Use the action received from Python server, or default to DEFEND
		if (pendingAction && pendingActionStackId == stack->unitId()) {
			print("Executing action from Python server: " + std::to_string(static_cast<int>(pendingAction->actionType)));
			executeAction(battleID, stack, *pendingAction);
			pendingAction.reset();
		} else {
			print("No action from Python server, using default DEFEND");
			cb->battleMakeUnitAction(battleID, BattleAction::makeDefend(stack));
		}
		actionReady = false;
		actionCV.notify_one();
	}
}

void CRLBattleAI::executeAction(const BattleID &battleID, const CStack *stack, const BattleAction &action)
{
	// Execute the action based on its type
	switch (action.actionType) {
		case EActionType::DEFEND:
			cb->battleMakeUnitAction(battleID, BattleAction::makeDefend(stack));
			break;
		case EActionType::WAIT:
			cb->battleMakeUnitAction(battleID, BattleAction::makeWait(stack));
			break;
		case EActionType::WALK: {
			if (!action.target.empty()) {
				BattleHex dest(action.target[0].hexValue);
				cb->battleMakeUnitAction(battleID, BattleAction::makeMove(stack, dest));
			} else {
				print("WALK action has no target, using DEFEND");
				cb->battleMakeUnitAction(battleID, BattleAction::makeDefend(stack));
			}
			break;
		}
		case EActionType::WALK_AND_ATTACK: {
			if (!action.target.empty()) {
				BattleHex dest(action.target[0].hexValue);
				// For now, assume we attack from current position
				BattleHex attackFrom(stack->getPosition());
				cb->battleMakeUnitAction(battleID, BattleAction::makeMeleeAttack(stack, dest, attackFrom, true));
			} else {
				print("WALK_AND_ATTACK action has no target, using DEFEND");
				cb->battleMakeUnitAction(battleID, BattleAction::makeDefend(stack));
			}
			break;
		}
		case EActionType::SHOOT: {
			if (!action.target.empty()) {
				// Find the target unit by ID
				auto targetUnit = cb->getBattle(battleID)->battleGetStackByID(action.target[0].unitValue);
				if (targetUnit) {
					cb->battleMakeUnitAction(battleID, BattleAction::makeShotAttack(stack, targetUnit));
				} else {
					print("SHOOT action target not found, using DEFEND");
					cb->battleMakeUnitAction(battleID, BattleAction::makeDefend(stack));
				}
			} else {
				print("SHOOT action has no target, using DEFEND");
				cb->battleMakeUnitAction(battleID, BattleAction::makeDefend(stack));
			}
			break;
		}
		default:
			print("Unknown action type " + std::to_string(static_cast<int>(action.actionType)) + ", using DEFEND");
			cb->battleMakeUnitAction(battleID, BattleAction::makeDefend(stack));
			break;
	}
}

BattleAction CRLBattleAI::deserializeAction(const std::vector<std::byte> &message)
{
	BattleAction action;

	// Deserialize raw BattleAction data (not as a polymorphic pack)
	// Format: side (1 byte), stackNumber (compact int), actionType (1 byte),
	//         spell (compact int), target (vector)
	const uint8_t *data = reinterpret_cast<const uint8_t *>(message.data());
	size_t pos = 0;
	size_t msgSize = message.size();

	if (msgSize < 4) {
		print("Message too short for BattleAction");
		action.actionType = EActionType::DEFEND;
		return action;
	}

	// Helper lambda to read compact integer
	auto readCompactInt = [&data, &pos, msgSize]() -> int32_t {
		if (pos >= msgSize) return 0;

		uint32_t value = 0;
		int offset = 0;

		while (pos < msgSize) {
			uint8_t byte = data[pos++];
			if (byte & 0x80) {
				value |= (byte & 0x7F) << offset;
				offset += 7;
			} else {
				value |= (byte & 0x3F) << offset;
				bool isNegative = (byte & 0x40) != 0;
				return isNegative ? -static_cast<int32_t>(value) : static_cast<int32_t>(value);
			}
		}
		return 0;
	};

	try {
		// side (int8)
		action.side = static_cast<BattleSide>(static_cast<int8_t>(data[pos++]));

		// stackNumber (compact int)
		action.stackNumber = readCompactInt();

		// actionType (int8)
		if (pos < msgSize) {
			action.actionType = static_cast<EActionType>(static_cast<int8_t>(data[pos++]));
		}

		// spell (compact int)
		if (pos < msgSize) {
			action.spell = SpellID(readCompactInt());
		}

		// target (vector of DestinationInfo)
		if (pos < msgSize) {
			int32_t targetSize = readCompactInt();
			for (int32_t i = 0; i < targetSize && pos < msgSize; ++i) {
				BattleAction::DestinationInfo dest;
				dest.unitValue = readCompactInt();
				if (pos + 1 < msgSize) {
					// BattleHex is just an int16
					dest.hexValue = BattleHex(static_cast<int16_t>(readCompactInt()));
				}
				action.target.push_back(dest);
			}
		}

		print("Deserialized action: side=" + std::to_string(static_cast<int>(action.side)) +
		      " stack=" + std::to_string(action.stackNumber) +
		      " type=" + std::to_string(static_cast<int>(action.actionType)));

	} catch (const std::exception &e) {
		print("Error deserializing action: " + std::string(e.what()));
		action.actionType = EActionType::DEFEND;
	}

	return action;
}

void CRLBattleAI::battleAttack(const BattleID & battleID, const BattleAttack *ba)
{
	print("battleAttack called");
}

void CRLBattleAI::battleStacksAttacked(const BattleID & battleID, const std::vector<BattleStackAttacked> & bsa, bool ranged)
{
	print("battleStacksAttacked called");
}

void CRLBattleAI::battleEnd(const BattleID & battleID, const BattleResult *br, QueryID queryID)
{
	print("battleEnd called");
}

// void CRLBattleAI::battleResultsApplied()
// {
// 	print("battleResultsApplied called");
// }

void CRLBattleAI::battleNewRoundFirst(const BattleID & battleID)
{
	print("battleNewRoundFirst called");
}

void CRLBattleAI::battleNewRound(const BattleID & battleID)
{
	print("battleNewRound called");
}

void CRLBattleAI::battleStackMoved(const BattleID & battleID, const CStack * stack, const BattleHexArray & dest, int distance, bool teleport)
{
	print("battleStackMoved called");
}

void CRLBattleAI::battleSpellCast(const BattleID & battleID, const BattleSpellCast *sc)
{
	print("battleSpellCast called");
}

void CRLBattleAI::battleStacksEffectsSet(const BattleID & battleID, const SetStackEffect & sse)
{
	print("battleStacksEffectsSet called");
}

void CRLBattleAI::battleStart(const BattleID & battleID, const CCreatureSet *army1, const CCreatureSet *army2, int3 tile, const CGHeroInstance *hero1, const CGHeroInstance *hero2, BattleSide Side, bool replayAllowed)
{
	print("battleStart called");
	side = Side;
}

void CRLBattleAI::battleCatapultAttacked(const BattleID & battleID, const CatapultAttack & ca)
{
	print("battleCatapultAttacked called");
}

// const std::shared_ptr<INetworkConnection> &, const std::vector<std::byte> & message
void CRLBattleAI::onPacketReceived(const std::shared_ptr<INetworkConnection> &, const std::vector<std::byte> &message) {
	print("Received packet from Python server, size: " + std::to_string(message.size()));

	// Deserialize the action from raw bytes (not as a CPack)
	BattleAction action = deserializeAction(message);

	std::unique_lock lk(actionMtx);
	actionCV.wait(lk, [this]{ return !actionReady; });

	// Store the action for use in activeStack
	pendingAction = std::make_unique<BattleAction>(action);
	pendingActionStackId = action.stackNumber;
	print("Stored action for stack " + std::to_string(pendingActionStackId));

	actionReady = true;
	actionCV.notify_one();
}

void CRLBattleAI::onConnectionFailed(const std::string &errorMessage) {
	logNetwork->info(errorMessage);
}

void CRLBattleAI::onConnectionEstablished(const NetworkConnectionPtr & netConnection) {
	networkConnection = netConnection;
	logNetwork->info("Connection established");
	logicConnection = std::make_shared<GameConnection>(netConnection);
}

void CRLBattleAI::onDisconnected(const std::shared_ptr<INetworkConnection> &, const std::string &errorMessage) {
}

void CRLBattleAI::print(const std::string &text) const
{
	logAi->info("CRLBattleAI  [%p]: %s", this, text);
}
