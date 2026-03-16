#!/usr/bin/env python3
"""
Test variant types are properly typed
"""

from vcmi_types import (
    BonusCustomSubtype, SpellID, CreatureID, PrimarySkill, TerrainId, GameResID, SpellSchool, BonusTypeID,
    BonusCustomSource, ArtifactID, CampaignScenarioID, SecondarySkill, HeroTypeID, Obj, ObjectInstanceID, BuildingTypeUniqueID, BattleField, ArtifactInstanceID
)

def test_variant_types():
    """Test that variant types maintain their type information"""
    print("Testing variant types...")

    # Test BonusSubtypeID variants
    print("\n--- Testing BonusSubtypeID variants ---")

    bonus_custom_subtype = BonusCustomSubtype(1)
    print(f"✓ BonusCustomSubtype: {bonus_custom_subtype.to_string()}")
    assert bonus_custom_subtype.to_int() == 1
    assert hasattr(bonus_custom_subtype, 'value')

    spell_id = SpellID(5)
    print(f"✓ SpellID: {spell_id.to_string()}")
    assert spell_id.to_int() == 5
    assert hasattr(spell_id, 'value')

    creature_id = CreatureID(10)
    print(f"✓ CreatureID: {creature_id.to_string()}")
    assert creature_id.to_int() == 10
    assert hasattr(creature_id, 'value')

    # Test BonusSourceID variants
    print("\n--- Testing BonusSourceID variants ---")

    artifact_id = ArtifactID(20)
    print(f"✓ ArtifactID: {artifact_id.to_string()}")
    assert artifact_id.to_int() == 20
    assert hasattr(artifact_id, 'value')

    object_instance_id = ObjectInstanceID(30)
    print(f"✓ ObjectInstanceID: {object_instance_id.to_string()}")
    assert object_instance_id.to_int() == 30
    assert hasattr(object_instance_id, 'value')

    hero_type_id = HeroTypeID(40)
    print(f"✓ HeroTypeID: {hero_type_id.to_string()}")
    assert hero_type_id.to_int() == 40
    assert hasattr(hero_type_id, 'value')

    print("\n✓ All variant types maintain type information correctly!")
    return True

if __name__ == "__main__":
    success = test_variant_types()
    exit(0 if success else 1)
