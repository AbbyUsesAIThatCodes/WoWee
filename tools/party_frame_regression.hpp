#pragma once

// Uses the real engine, bindings, extracted FrameXML and widget tree. The only
// fixture is roster/entity data; no connection or rendering device is created.
#include "addons/addon_manager.hpp"
#include "game/game_handler.hpp"
#include <algorithm>
#include <cstdio>

inline bool runPartyFrameRegression(wowee::addons::AddonManager& mgr,
                                    wowee::game::GameHandler& gh) {
    auto* engine = mgr.getLuaEngine();
    auto check = [&](const char* label, const std::string& code) {
        const bool ok = engine->executeString(code);
        std::printf("party regression: %s: %s\n", label, ok ? "PASS" : "FAIL");
        return ok;
    };
    bool ok = check("real FrameXML loaded", R"LUA(
        assert(type(PartyMemberFrame_UpdateMember) == 'function')
        for i=1,4 do assert(type(_G['PartyMemberFrame'..i]) == 'table') end
        HIDE_PARTY_INTERFACE = '0'
        UIParent:Show()
    )LUA");
    if (!ok) return false;

    // GameHandler owns a mutable roster; const_cast is confined to this test
    // fixture so production does not gain a test-only mutation API.
    auto& roster = const_cast<wowee::game::GroupListData&>(gh.getPartyData());
    roster = {};
    auto changed = [&]() {
        roster.memberCount = static_cast<uint32_t>(roster.members.size());
        mgr.fireEvent("GROUP_ROSTER_UPDATE");
        mgr.fireEvent("PARTY_MEMBERS_CHANGED");
        engine->updateVisibility();
    };
    changed();
    ok &= check("empty roster", R"LUA(
        assert(GetNumPartyMembers() == 0)
        for i=1,4 do
            assert(not GetPartyMember(i))
            assert(not UnitExists('party'..i))
            assert(not _G['PartyMemberFrame'..i]:IsShown())
        end
    )LUA");

    for (int i = 1; i <= 4; ++i) {
        wowee::game::GroupMember member;
        member.guid = 100 + i;
        member.name = "Companion" + std::to_string(i);
        member.isOnline = i == 4 ? 0 : 1;
        member.onlineStatus = member.isOnline;
        member.level = 80;
        roster.members.push_back(member);
    }
    changed();
    ok &= check("roster identity before any stats packet", R"LUA(
        for i=1,4 do
            local unit = 'party'..i
            assert(GetPartyMember(i) and UnitExists(unit), 'roster missing '..unit)
            assert(UnitName(unit) == 'Companion'..i)
            assert(_G['PartyMemberFrame'..i]:IsVisible())
            assert(_G['PartyMemberFrame'..i..'Name']:GetText() == 'Companion'..i)
            assert(UnitHealth(unit) == 0 and UnitHealthMax(unit) == 0)
        end
    )LUA");
    for (int i = 1; i <= 4; ++i) {
        auto& m = roster.members[static_cast<size_t>(i - 1)];
        m.hasPartyStats = true;
        m.curHealth = 100 * i;
        m.maxHealth = 1000;
        mgr.fireEvent("UNIT_HEALTH", {"party" + std::to_string(i)});
    }
    ok &= check("four members, including offline and outside entity range", R"LUA(
        assert(GetNumPartyMembers() == 4)
        for i=1,4 do
            local unit, frame = 'party'..i, _G['PartyMemberFrame'..i]
            assert(GetPartyMember(i), 'membership gate false for '..unit)
            assert(UnitExists(unit), 'missing '..unit)
            assert(frame:IsVisible(), 'hidden '..unit)
            assert(UnitName(unit) == 'Companion'..i)
            assert(UnitHealth(unit) == 100*i and UnitHealthMax(unit) == 1000)
            assert(_G[frame:GetName()..'Name']:GetText() == 'Companion'..i)
            -- Offline bars are deliberately full and grey in WotLK FrameXML.
            local shownHealth = i == 4 and 1000 or 100*i
            assert(_G[frame:GetName()..'HealthBar']:GetValue() == shownHealth)
        end
        assert(not UnitIsConnected('party4'))
        for _,i in ipairs({-1,0,5,40,1.5}) do assert(not GetPartyMember(i)) end
    )LUA");
    for (int i = 1; i <= 4; ++i) {
        const auto unit = "party" + std::to_string(i);
        const auto* portrait = engine->widgets().findByName(
            "PartyMemberFrame" + std::to_string(i) + "Portrait");
        const auto& claimed = engine->widgets().portraitsFor(unit);
        const bool bound = portrait &&
            std::find(claimed.begin(), claimed.end(), portrait->id) != claimed.end();
        std::printf("party regression: %s portrait binding: %s\n",
                    unit.c_str(), bound ? "PASS" : "FAIL");
        ok &= bound;
    }

    // A visible entity takes priority over the out-of-range roster snapshot.
    auto member = std::make_shared<wowee::game::Player>(101);
    member->setName("NearbyCompanion");
    member->setHealth(725);
    member->setMaxHealth(1200);
    gh.getEntityManager().addEntity(101, member);
    changed();
    ok &= check("nearby entity name and health", R"LUA(
        assert(GetPartyMember(1) and UnitExists('party1'))
        assert(UnitName('party1') == 'NearbyCompanion')
        assert(UnitHealth('party1') == 725 and UnitHealthMax('party1') == 1200)
        assert(PartyMemberFrame1Name:GetText() == 'NearbyCompanion')
        assert(PartyMemberFrame1HealthBar:GetValue() == 725)
    )LUA");

    roster.members.erase(roster.members.begin());
    changed();
    ok &= check("leave compacts slots and hides the absent fourth", R"LUA(
        assert(GetNumPartyMembers() == 3)
        for i=1,3 do
            assert(GetPartyMember(i) and _G['PartyMemberFrame'..i]:IsVisible())
            assert(UnitName('party'..i) == 'Companion'..(i+1))
            assert(UnitHealth('party'..i) == 100*(i+1))
        end
        assert(not GetPartyMember(4) and not UnitExists('party4'))
        assert(not PartyMemberFrame4:IsShown())
    )LUA");

    wowee::game::GroupMember joined;
    joined.guid = 105;
    joined.name = "NewCompanion";
    joined.isOnline = 1;
    joined.onlineStatus = 1;
    joined.curHealth = 550;
    joined.maxHealth = 900;
    joined.hasPartyStats = true;
    roster.members.push_back(joined);
    changed();
    ok &= check("join refills and shows the fourth slot", R"LUA(
        assert(GetPartyMember(4) and PartyMemberFrame4:IsVisible())
        assert(UnitName('party4') == 'NewCompanion')
        assert(PartyMemberFrame4Name:GetText() == 'NewCompanion')
        assert(PartyMemberFrame4HealthBar:GetValue() == 550)
    )LUA");
    roster = {};
    changed();
    ok &= check("disband clears all slots", R"LUA(
        for i=1,4 do
            assert(not GetPartyMember(i) and not UnitExists('party'..i))
            assert(not _G['PartyMemberFrame'..i]:IsShown())
        end
    )LUA");
    engine->setGameHandler(nullptr);
    ok &= check("no game handler", "assert(not GetPartyMember(1))");
    engine->setGameHandler(&gh);
    return ok;
}
