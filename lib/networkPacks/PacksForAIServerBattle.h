/*
 * PacksForAIServerBattle.h, part of VCMI engine
 *
 * Authors: listed in file AUTHORS in main folder
 *
 * License: GNU General Public License v2.0 or later
 * Full text of license available in license.txt file, in main folder
 *
 */
#pragma once

#include "NetPacksBase.h"
#include "BattleChanges.h"
#include "../battle/BattleHexArray.h"
#include "../battle/BattleAction.h"
#include "../texts/MetaString.h"
#include "../../Global.h"

class CClient;

VCMI_LIB_NAMESPACE_BEGIN

// class CGHeroInstance;
// class CArmedInstance;
class CGameState;
class ICPackVisitor;
class BattleID;
class BattleInfo;

struct DLL_LINKAGE BattleStateUpdate : public CPackForClient
{
	void applyGs(CGameState * gs) override;

	BattleID battleID = BattleID::NONE;
	BattleInfo * info = nullptr;

	void visitTyped(ICPackVisitor & visitor) override;

	template <typename Handler> void serialize(Handler & h)
	{
		h & battleID;
		h & info;
		assert(battleID != BattleID::NONE);
	}
};

VCMI_LIB_NAMESPACE_END
