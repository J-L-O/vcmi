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
#include "lib/battle/CBattleInfoCallback.h"
#include "lib/battle/CPlayerBattleCallback.h"
#include "lib/battle/CObstacleInstance.h"
#include "lib/network/NetworkHandler.h"
#include "lib/networkPacks/PacksForClientBattle.h"
#include "lib/networkPacks/BattleStateForAI.h"
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

	if (const char * envPort = std::getenv("VCMI_RL_PORT"))
	{
		port = static_cast<uint16_t>(std::stoi(envPort));
	}

	networkHandler->connectToRemote(*this, hostname, port);

	print("created, connecting to port " + std::to_string(port));
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
	print("activeStack called for " + stack->nodeName());

	auto battle = cb->getBattle(battleID);

	BattleStateForAI pack;
	pack.battleId = battleID.getNum();
	pack.round = currentRound;
	pack.activeStackId = stack->unitId();
	pack.activeSide = static_cast<int8_t>(stack->unitSide());

	// Battlefield metadata
	pack.terrainType = static_cast<int32_t>(battle->battleTerrainType());
	pack.battlefieldType = static_cast<int32_t>(battle->getBattle()->getBattlefieldType());

	const CGTownInstance * town = battle->battleGetDefendedTown();
	pack.isSiege = (town != nullptr);

	// Sides
	auto fillSide = [&](AISideState & out, BattleSide side)
	{
		out.color = static_cast<int8_t>(battle->getBattle()->getSidePlayer(side).getNum());
		out.hasHero = battle->battleHasHero(side);
		const auto * hero = battle->getBattle()->getSideHero(side);
		out.heroId = hero ? hero->id.getNum() : -1;
		out.castSpellsCount = battle->getBattle()->getCastSpells(side);
		out.mana = hero ? hero->mana : 0;
		out.enchanterCounter = battle->getBattle()->getEnchanterCounter(side);
	};
	fillSide(pack.attacker, BattleSide::ATTACKER);
	fillSide(pack.defender, BattleSide::DEFENDER);

	// Wall state (siege)
	if (pack.isSiege)
	{
		pack.walls.wallParts.resize(static_cast<int>(EWallPart::PARTS_COUNT), static_cast<int8_t>(EWallState::NONE));
		for (int i = 0; i < static_cast<int>(EWallPart::PARTS_COUNT); ++i)
		{
			pack.walls.wallParts[i] = static_cast<int8_t>(
				battle->getBattle()->getWallState(static_cast<EWallPart>(i)));
		}
		pack.walls.gateState = static_cast<int8_t>(battle->getBattle()->getGateState());
	}

	// Stacks
	auto allStacks = battle->battleGetAllStacks(true); // include turrets
	for (const CStack * s : allStacks)
	{
		AIStackState ss;
		ss.id = s->unitId();
		ss.creatureId = s->unitType() ? s->unitType()->getId().getNum() : -1;
		ss.count = s->getCount();
		ss.firstHPLeft = s->getFirstHPleft();
		ss.maxHP = s->getMaxHealth();
		ss.totalHP = s->getAvailableHealth();
		ss.baseAmount = s->unitBaseAmount();
		ss.killed = s->getKilled();

		ss.attack = s->getAttack(false);
		ss.defense = s->getDefense(false);
		ss.rangedAttack = s->getAttack(true);
		ss.rangedDefense = s->getDefense(true);
		ss.minDamage = s->getMinDamage(false);
		ss.maxDamage = s->getMaxDamage(false);
		ss.minRangedDamage = s->getMinDamage(true);
		ss.maxRangedDamage = s->getMaxDamage(true);
		ss.speed = s->getMovementRange();
		ss.initiative = s->getInitiative();

		ss.position = s->getPosition().toInt();
		ss.initialPosition = s->initialPosition.toInt();

		ss.side = static_cast<int8_t>(s->unitSide());
		ss.slot = static_cast<int8_t>(s->unitSlot().getNum());
		ss.owner = static_cast<int8_t>(s->unitOwner().getNum());

		ss.alive = s->alive();
		ss.isShooter = s->isShooter();
		ss.canShoot = s->canShoot();
		ss.doubleWide = s->doubleWide();
		ss.defending = s->defended();
		ss.moved = s->moved();
		ss.waiting = s->waited();
		ss.canMove = s->canMove();
		ss.isCaster = s->isCaster();
		ss.canCast = s->canCast();
		ss.isClone = s->isClone();
		ss.isSummoned = s->summoned;
		ss.isGhost = s->isGhost();
		ss.isFrozen = s->isFrozen();
		ss.isHypnotized = s->isHypnotized();
		ss.canRetaliate = s->ableToRetaliate();

		ss.shotsLeft = s->shots.available();
		ss.shotsTotal = s->shots.total();
		ss.castsLeft = s->casts.available();
		ss.retaliationsLeft = s->counterAttacks.available();
		ss.retaliationsTotal = s->counterAttacks.total();

		ss.level = s->unitType() ? s->unitType()->getLevel() : 0;

		pack.stacks.push_back(ss);
	}

	// Obstacles
	auto allObstacles = battle->getBattle()->getAllObstacles();
	for (const auto & obs : allObstacles)
	{
		AIObstacleState os;
		os.id = obs->uniqueID;
		os.obstacleId = obs->ID;
		os.position = obs->pos.toInt();
		os.obstacleType = static_cast<int8_t>(obs->obstacleType);

		auto blockedTiles = obs->getBlockedTiles();
		for (auto hex : blockedTiles)
			os.blockedHexes.push_back(hex.toInt());

		// Spell-created obstacle extra data
		if (auto * spellObs = dynamic_cast<const SpellCreatedObstacle *>(obs.get()))
		{
			os.turnsRemaining = spellObs->turnsRemaining;
			os.spellPower = spellObs->casterSpellPower;
			os.minimalDamage = spellObs->minimalDamage;
			os.casterSide = static_cast<int8_t>(spellObs->casterSide);
			os.passable = spellObs->passable;
			os.trap = spellObs->trap;
		}

		pack.obstacles.push_back(os);
	}

	// Reachable hexes for the active stack
	auto reachableHexes = battle->battleGetAvailableHexes(stack, true);
	for (auto hex : reachableHexes)
		pack.reachableHexes.push_back(hex.toInt());

	// Attackable targets: for each enemy alive stack, find attack hexes
	for (const CStack * enemy : allStacks)
	{
		if (!enemy->alive() || enemy->unitSide() == stack->unitSide())
			continue;

		if (stack->canShoot())
		{
			// Ranged: can attack this target from current position
			pack.attackableTargets.push_back(enemy->unitId());
			pack.attackableTargets.push_back(stack->getPosition().toInt());
		}
		else
		{
			// Melee: find hexes from which we can attack this enemy
			auto attackHexes = CStack::meleeAttackHexes(stack, enemy);
			for (auto hex : attackHexes)
			{
				pack.attackableTargets.push_back(enemy->unitId());
				pack.attackableTargets.push_back(hex.toInt());
			}
		}
	}

	logicConnection->sendPack(pack);

	{
		std::unique_lock lk(actionMtx);
		actionCV.wait(lk, [this]{ return actionReady; });

		// Override stack identity from the actual stack
		nextAction.stackNumber = stack->unitId();
		nextAction.side = stack->unitSide();
		print("Executing action type=" + std::to_string(static_cast<int>(nextAction.actionType))
			+ " for stack=" + std::to_string(nextAction.stackNumber));
		cb->battleMakeUnitAction(battleID, nextAction);
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
	print("battleEnd called, winner=" + std::to_string(static_cast<int>(br->winner))
		+ " result=" + std::to_string(static_cast<int>(br->result)));

	if (logicConnection)
	{
		BattleEndForAI pack;
		pack.battleId = battleID.getNum();
		pack.winner = static_cast<int8_t>(br->winner);
		pack.result = static_cast<int8_t>(br->result);
		pack.ourSide = static_cast<int8_t>(side);
		logicConnection->sendPack(pack);
	}
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
	currentRound++;
	print("battleNewRound called, round=" + std::to_string(currentRound));
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
	currentRound = 0;
}

void CRLBattleAI::battleCatapultAttacked(const BattleID & battleID, const CatapultAttack & ca)
{
	print("battleCatapultAttacked called");
}

void CRLBattleAI::onPacketReceived(const std::shared_ptr<INetworkConnection> &, const std::vector<std::byte> &message) {
	print("onPacketReceived: got " + std::to_string(message.size()) + " bytes");

	BattleAction receivedAction;
	try
	{
		auto pack = logicConnection->retrievePack(message);
		print("Pack deserialized: " + std::string(typeid(*pack).name()));

		auto * makeAction = dynamic_cast<MakeAction *>(pack.get());
		if (makeAction)
		{
			receivedAction = makeAction->ba;
			print("Received action from Python: type=" + std::to_string(static_cast<int>(receivedAction.actionType)));
		}
		else
		{
			logAi->error("CRLBattleAI: unexpected pack type: %s", typeid(*pack).name());
			receivedAction.actionType = EActionType::DEFEND;
		}
	}
	catch (const std::exception & e)
	{
		logAi->error("CRLBattleAI: deserialization failed: %s", e.what());
		receivedAction.actionType = EActionType::DEFEND;
	}

	std::unique_lock lk(actionMtx);
	actionCV.wait(lk, [this]{ return !actionReady; });

	nextAction = receivedAction;
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
