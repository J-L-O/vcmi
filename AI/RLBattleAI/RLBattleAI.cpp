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

	BattleStart pack;
	pack.battleID = battleID;

	int3 tile = cb->getBattle(battleID)->getBattle()->getLocation();
	TerrainId terrain = cb->getBattle(battleID)->battleTerrainType();
	BattleField battlefieldType = cb->getBattle(battleID)->getBattle()->getBattlefieldType();
	BattleLayout layout = cb->getBattle(battleID)->getBattle()->getLayout();
	const CGTownInstance *town = cb->getBattle(battleID)->battleGetDefendedTown();

	const CArmedInstance *army1 = cb->getBattle(battleID)->getBattle()->getSideArmy(BattleSide::ATTACKER);
	const CArmedInstance *army2 = cb->getBattle(battleID)->getBattle()->getSideArmy(BattleSide::DEFENDER);
	BattleSideArray<const CArmedInstance *> armies{army1, army2};

	const CGHeroInstance *hero1 = cb->getBattle(battleID)->getBattle()->getSideHero(BattleSide::ATTACKER);
	const CGHeroInstance *hero2 = cb->getBattle(battleID)->getBattle()->getSideHero(BattleSide::DEFENDER);
	BattleSideArray<const CGHeroInstance*>heroes{hero1, hero2};

	pack.info = BattleInfo::setupBattle(const_cast<IGameInfoCallback*>(env->game()), tile, terrain, battlefieldType, armies, heroes, layout, town);
	
	// Debug: Print BattleInfo contents in serialization order
	if (pack.info) {
		print("BattleInfo serialization contents:");
		print("  battleID: " + std::to_string(pack.info->battleID.getNum()));
		
		// sides array - using public getSide methods
		const auto& attackerSide = pack.info->getSide(BattleSide::ATTACKER);
		const auto& defenderSide = pack.info->getSide(BattleSide::DEFENDER);
		
		print("  sides[0] (attacker):");
		print("    color: " + std::to_string(static_cast<int>(attackerSide.color)));
		print("    heroID: " + ObjectInstanceID::encode(attackerSide.heroID.getNum()));
		print("    armyObjectID: " + ObjectInstanceID::encode(attackerSide.armyObjectID.getNum()));
		print("    castSpellsCount: " + std::to_string(attackerSide.castSpellsCount));
		print("    usedSpellsHistory size: " + std::to_string(attackerSide.usedSpellsHistory.size()));
		print("    enchanterCounter: " + std::to_string(attackerSide.enchanterCounter));
		print("    initialMana: " + std::to_string(attackerSide.initialMana));
		print("    additionalMana: " + std::to_string(attackerSide.additionalMana));
		
		print("  sides[1] (defender):");
		print("    color: " + std::to_string(static_cast<int>(defenderSide.color)));
		print("    heroID: " + ObjectInstanceID::encode(defenderSide.heroID.getNum()));
		print("    armyObjectID: " + ObjectInstanceID::encode(defenderSide.armyObjectID.getNum()));
		print("    castSpellsCount: " + std::to_string(defenderSide.castSpellsCount));
		print("    usedSpellsHistory size: " + std::to_string(defenderSide.usedSpellsHistory.size()));
		print("    enchanterCounter: " + std::to_string(defenderSide.enchanterCounter));
		print("    initialMana: " + std::to_string(defenderSide.initialMana));
		print("    additionalMana: " + std::to_string(defenderSide.additionalMana));
		
		print("  round: " + std::to_string(pack.info->round));
		print("  activeStack: " + std::to_string(pack.info->activeStack));
		print("  townID: " + ObjectInstanceID::encode(pack.info->townID.getNum()));
		print("  tile: " + pack.info->tile.toString());
		print("  stacks count: " + std::to_string(pack.info->stacks.size()));
		print("  obstacles count: " + std::to_string(pack.info->obstacles.size()));
		
		// SiegeInfo
		print("  siegeInfo:");
		print("    wallState size: " + std::to_string(pack.info->si.wallState.size()));
		print("    gateState: " + std::to_string(static_cast<int>(pack.info->si.gateState)));
		
		print("  battlefieldType: " + std::to_string(static_cast<int>(pack.info->battlefieldType)));
		print("  terrainType: " + std::to_string(static_cast<int>(pack.info->terrainType)));
		print("  tacticsSide: " + std::to_string(static_cast<int>(pack.info->tacticsSide)));
		print("  tacticDistance: " + std::to_string(pack.info->tacticDistance));
		
		// CBonusSystemNode fields (basic info)
		print("  CBonusSystemNode:");
		auto& bonuses = pack.info->getExportedBonusList();
		print("    exported bonuses count: " + std::to_string(bonuses.size()));

		// Log each bonus for debugging
		for (const auto& bonus : bonuses)
		{
			print("    Bonus:");
			print("      duration: " + std::to_string(static_cast<int>(bonus->duration)));
			print("      type: " + std::to_string(static_cast<int>(bonus->type)));
			print("      subtype: " + bonus->subtype.toString());
			print("      source: " + std::to_string(static_cast<int>(bonus->source)));
			print("      val: " + std::to_string(bonus->val));
			print("      sid: " + bonus->sid.toString());
			print("      valType: " + std::to_string(static_cast<int>(bonus->valType)));
			print("      turnsRemain: " + std::to_string(bonus->turnsRemain));
			print("      effectRange: " + std::to_string(static_cast<int>(bonus->effectRange)));
			print("      targetSourceType: " + std::to_string(static_cast<int>(bonus->targetSourceType)));
		}
		
		print("  replayAllowed: " + std::string(pack.info->replayAllowed ? "true" : "false"));
	}
	
	logicConnection->sendPack(pack);

	{
		std::unique_lock lk(actionMtx);
		actionCV.wait(lk, [this]{ return actionReady; });

		cb->battleMakeUnitAction(battleID, BattleAction::makeDefend(stack));
		actionReady = false;
		actionCV.notify_one();
	}
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
	// std::unique_ptr<CPack> pack = logicConnection->retrievePack(message);
	auto pack = logicConnection->retrievePack(message);

	std::unique_lock lk(actionMtx);
	actionCV.wait(lk, [this]{ return !actionReady; });

	// TODO: Set nextAction from pack contents
	actionReady = true;
	actionCV.notify_one();
	// ServerHandlerCPackVisitor visitor(*this);
	// pack->visit(visitor);
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
