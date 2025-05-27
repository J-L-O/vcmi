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

#include <boost/asio/connect.hpp>
#include <boost/asio/io_context.hpp>
#include <boost/asio/ip/tcp.hpp>

#include "CThreadHelper.h"
#include "../../lib/CStack.h"
#include "../../CCallback.h"
#include "../../lib/battle/BattleAction.h"
#include "../../lib/battle/BattleInfo.h"
#include "client/ConditionalWait.h"
#include "../../lib/network/NetworkHandler.h"
#include "../../lib/networkPacks/PacksForAIServerBattle.h"
// #include "networkPacks/PacksForClientBattle.h"


CRLBattleAI::CRLBattleAI()
	: side(BattleSide::NONE)
	//, resolver(io_context)
	//, endpoints(resolver.resolve("127.0.0.1", "65432"))
	, networkHandler(INetworkHandler::createHandler())
	//, context(std::make_shared<NetworkContext>())
	//, socket(std::make_shared<NetworkSocket>(*context))
	//, networkConnection(std::make_shared<NetworkConnection>(*this, socket, context))
	//, connection(std::make_shared<CConnection>(networkConnection))
	, threadNetwork(&CRLBattleAI::threadRunNetwork, this)
	, wasWaitingForRealize(false)
	, wasUnlockingGs(false)
{
	//boost::asio::connect(socket, endpoints);
	// void GlobalLobbyClient::connect()
	// {
	// 	std::string hostname = getServerHost();
	// 	uint16_t port = getServerPort();
	// 	CSH->getNetworkHandler().connectToRemote(*this, hostname, port);
	// }

	std::string hostname = "127.0.0.1";
	uint16_t port = 65432;
	// std::unique_ptr<INetworkHandler> networkHandler = NetworkHandler::createHandler();
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

	BattleStateUpdate pack;
	pack.battleID = battleID;
	pack.info = cb->getBattle(battleID)->getBattle();
	logicConnection->sendPack(pack);  // TODO: Need to make sure that connection is actually established at this point

	cb->battleMakeUnitAction(battleID, BattleAction::makeDefend(stack));
	return;
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
	// ServerHandlerCPackVisitor visitor(*this);
	// pack->visit(visitor);
}

void CRLBattleAI::onConnectionFailed(const std::string &errorMessage) {
}

void CRLBattleAI::onConnectionEstablished(const NetworkConnectionPtr & netConnection) {
	networkConnection = netConnection;

	logNetwork->info("Connection established");

	logicConnection = std::make_shared<CConnection>(netConnection);
	// logicConnection->uuid = uuid;
	// logicConnection->enterLobbyConnectionMode();
}

void CRLBattleAI::onDisconnected(const std::shared_ptr<INetworkConnection> &, const std::string &errorMessage) {
}

void CRLBattleAI::print(const std::string &text) const
{
	logAi->trace("CRLBattleAI  [%p]: %s", this, text);
}
