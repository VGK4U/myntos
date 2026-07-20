"""
Test partial point consumption in matching award breakdown allocation.

This test verifies that the incremental allocation logic correctly handles:
1. Platinum packages (1.0 points)
2. Diamond packages (0.5 points) - future support
3. Partial consumption when members span tier boundaries
4. Correct split of members across skipped, allocated, and surplus categories
"""

import pytest
from typing import List, Dict, Any


def split_leg_members_incremental(members: List[Dict[str, Any]], skip_points: float, allocate_points: float):
    """
    Extracted allocation logic from award_processing.py for testing.
    """
    skipped = []
    allocated = []
    surplus = []
    cumulative_points = 0.0
    
    for member in members:
        member_points = float(member['points'])
        member_start = cumulative_points
        member_end = cumulative_points + member_points
        
        # Case 1: Member entirely consumed by previous tiers
        if member_end <= skip_points:
            skipped.append(member.copy())
            cumulative_points = member_end
        
        # Case 2: Member spans skip boundary (partially consumed by previous tiers)
        elif member_start < skip_points < member_end:
            # Portion consumed by previous tiers
            consumed_portion = skip_points - member_start
            remaining_portion = member_points - consumed_portion
            
            # Add consumed portion to skipped
            if consumed_portion > 0:
                skipped_member = member.copy()
                skipped_member['points'] = round(consumed_portion, 2)
                skipped_member['partial'] = True
                skipped_member['original_points'] = member_points
                skipped.append(skipped_member)
            
            # Calculate how much budget is left for THIS tier
            already_allocated = sum(m['points'] for m in allocated)
            budget_remaining = allocate_points - already_allocated
            
            # Check if remaining portion fits within budget
            if remaining_portion <= budget_remaining:
                # Entire remaining portion allocated to THIS tier
                allocated_member = member.copy()
                allocated_member['points'] = round(remaining_portion, 2)
                allocated_member['partial'] = True
                allocated_member['original_points'] = member_points
                allocated.append(allocated_member)
            else:
                # Split: some to THIS tier, rest to surplus
                if budget_remaining > 0:
                    allocated_member = member.copy()
                    allocated_member['points'] = round(budget_remaining, 2)
                    allocated_member['partial'] = True
                    allocated_member['original_points'] = member_points
                    allocated.append(allocated_member)
                
                surplus_portion = remaining_portion - budget_remaining
                if surplus_portion > 0:
                    surplus_member = member.copy()
                    surplus_member['points'] = round(surplus_portion, 2)
                    surplus_member['partial'] = True
                    surplus_member['original_points'] = member_points
                    surplus.append(surplus_member)
            
            cumulative_points = member_end
        
        # Case 3: Member entirely in allocation range for THIS tier
        elif skip_points <= member_start < skip_points + allocate_points:
            # Calculate how much budget is left for THIS tier
            already_allocated = sum(m['points'] for m in allocated)
            budget_remaining = allocate_points - already_allocated
            
            if member_points <= budget_remaining:
                # Fully allocated to THIS tier
                allocated.append(member.copy())
            else:
                # Partially allocated, rest is surplus
                if budget_remaining > 0:
                    allocated_member = member.copy()
                    allocated_member['points'] = round(budget_remaining, 2)
                    allocated_member['partial'] = True
                    allocated_member['original_points'] = member_points
                    allocated.append(allocated_member)
                
                surplus_portion = member_points - budget_remaining
                if surplus_portion > 0:
                    surplus_member = member.copy()
                    surplus_member['points'] = round(surplus_portion, 2)
                    surplus_member['partial'] = True
                    surplus_member['original_points'] = member_points
                    surplus.append(surplus_member)
            
            cumulative_points = member_end
        
        # Case 4: Member entirely in surplus range
        else:
            surplus.append(member.copy())
            cumulative_points = member_end
    
    return allocated, surplus, skipped


class TestPartialPointAllocation:
    """Test suite for partial point consumption in matching awards."""
    
    def test_all_platinum_packages_star_award(self):
        """Test Star Award (1 match) with all Platinum (1.0 pts) members."""
        members = [
            {'user_id': 'USER1', 'name': 'User 1', 'points': 1.0},
            {'user_id': 'USER2', 'name': 'User 2', 'points': 1.0},
            {'user_id': 'USER3', 'name': 'User 3', 'points': 1.0},
        ]
        
        # Star Award: skip=0, allocate=1
        allocated, surplus, skipped = split_leg_members_incremental(members, skip_points=0, allocate_points=1.0)
        
        assert len(allocated) == 1, "Star should allocate 1 member"
        assert len(skipped) == 0, "Star should skip 0 members"
        assert len(surplus) == 2, "Star should have 2 surplus members"
        assert allocated[0]['user_id'] == 'USER1'
        assert sum(m['points'] for m in allocated) == 1.0
    
    def test_all_platinum_packages_prime_star_award(self):
        """Test Prime Star Award (3 total, 2 incremental) with all Platinum members."""
        members = [
            {'user_id': 'USER1', 'name': 'User 1', 'points': 1.0},
            {'user_id': 'USER2', 'name': 'User 2', 'points': 1.0},
            {'user_id': 'USER3', 'name': 'User 3', 'points': 1.0},
            {'user_id': 'USER4', 'name': 'User 4', 'points': 1.0},
        ]
        
        # Prime Star: skip=1 (Star consumed), allocate=2 (incremental)
        allocated, surplus, skipped = split_leg_members_incremental(members, skip_points=1.0, allocate_points=2.0)
        
        assert len(skipped) == 1, "Should skip 1 member (consumed by Star)"
        assert len(allocated) == 2, "Prime Star should allocate 2 members"
        assert len(surplus) == 1, "Should have 1 surplus member"
        assert skipped[0]['user_id'] == 'USER1'
        assert allocated[0]['user_id'] == 'USER2'
        assert allocated[1]['user_id'] == 'USER3'
        assert sum(m['points'] for m in allocated) == 2.0
    
    def test_mixed_diamond_platinum_star_award(self):
        """Test Star Award with mixed Diamond (0.5 pts) and Platinum (1.0 pts) packages."""
        members = [
            {'user_id': 'USER1', 'name': 'User 1', 'points': 0.5},  # Diamond
            {'user_id': 'USER2', 'name': 'User 2', 'points': 1.0},  # Platinum
            {'user_id': 'USER3', 'name': 'User 3', 'points': 0.5},  # Diamond
        ]
        
        # Star Award: skip=0, allocate=1.0
        allocated, surplus, skipped = split_leg_members_incremental(members, skip_points=0, allocate_points=1.0)
        
        assert len(skipped) == 0
        assert len(allocated) == 2, "Should allocate USER1 (0.5) + USER2 (0.5 partial) = 1.0"
        assert len(surplus) == 2, "Should have USER2 partial (0.5) + USER3 whole (0.5) in surplus"
        
        # Verify partial consumption
        assert allocated[0]['user_id'] == 'USER1'
        assert allocated[0]['points'] == 0.5
        assert 'partial' not in allocated[0] or not allocated[0].get('partial')
        
        assert allocated[1]['user_id'] == 'USER2'
        assert allocated[1]['points'] == 0.5
        assert allocated[1].get('partial') == True
        assert allocated[1].get('original_points') == 1.0
        
        assert surplus[0]['user_id'] == 'USER2'
        assert surplus[0]['points'] == 0.5
        assert surplus[0].get('partial') == True
        
        assert surplus[1]['user_id'] == 'USER3'
        assert surplus[1]['points'] == 0.5
    
    def test_partial_consumption_across_boundaries(self):
        """Test member spanning tier boundary - partial consumption."""
        members = [
            {'user_id': 'USER1', 'name': 'User 1', 'points': 1.5},  # Hypothetical multi-point
            {'user_id': 'USER2', 'name': 'User 2', 'points': 1.0},
        ]
        
        # Star Award: skip=0, allocate=1.0
        allocated, surplus, skipped = split_leg_members_incremental(members, skip_points=0, allocate_points=1.0)
        
        assert len(allocated) == 1, f"Expected 1 allocated, got {len(allocated)}"
        assert allocated[0]['user_id'] == 'USER1', f"Expected USER1, got {allocated[0]['user_id']}"
        assert allocated[0]['points'] == 1.0, f"Should allocate only 1.0 of 1.5, got {allocated[0]['points']}"
        assert allocated[0].get('partial') == True, "Should be marked as partial"
        assert allocated[0].get('original_points') == 1.5, f"Original should be 1.5, got {allocated[0].get('original_points')}"
        
        assert len(surplus) == 2, f"Expected 2 surplus (USER1 partial + USER2), got {len(surplus)}"
        assert surplus[0]['user_id'] == 'USER1', f"First surplus should be USER1, got {surplus[0]['user_id']}"
        assert surplus[0]['points'] == 0.5, f"Remaining 0.5 should be surplus, got {surplus[0]['points']}"
        assert surplus[0].get('partial') == True, "Should be marked as partial"
        
        assert surplus[1]['user_id'] == 'USER2', "Second surplus should be USER2 (whole member)"
    
    def test_no_double_counting(self):
        """Verify same member doesn't appear in multiple categories without partial flag."""
        members = [
            {'user_id': 'USER1', 'name': 'User 1', 'points': 1.0},
            {'user_id': 'USER2', 'name': 'User 2', 'points': 1.0},
        ]
        
        # Star Award
        allocated_star, surplus_star, skipped_star = split_leg_members_incremental(
            members, skip_points=0, allocate_points=1.0
        )
        
        # Prime Star (skip Star's 1.0, allocate 2.0 more)
        allocated_prime, surplus_prime, skipped_prime = split_leg_members_incremental(
            members, skip_points=1.0, allocate_points=2.0
        )
        
        # Star should show USER1
        assert len(allocated_star) == 1
        assert allocated_star[0]['user_id'] == 'USER1'
        
        # Prime Star should skip USER1, show USER2
        assert len(skipped_prime) == 1
        assert skipped_prime[0]['user_id'] == 'USER1'
        assert len(allocated_prime) == 1
        assert allocated_prime[0]['user_id'] == 'USER2'
        
        # No overlap in non-partial members
        star_ids = {m['user_id'] for m in allocated_star if not m.get('partial')}
        prime_ids = {m['user_id'] for m in allocated_prime if not m.get('partial')}
        assert len(star_ids & prime_ids) == 0, "No double-counting without partial flag"
    
    def test_edge_case_exact_boundary(self):
        """Test exact boundary match - no partial consumption."""
        members = [
            {'user_id': 'USER1', 'name': 'User 1', 'points': 1.0},
            {'user_id': 'USER2', 'name': 'User 2', 'points': 1.0},
        ]
        
        allocated, surplus, skipped = split_leg_members_incremental(members, skip_points=1.0, allocate_points=1.0)
        
        assert len(skipped) == 1
        assert len(allocated) == 1
        assert len(surplus) == 0
        assert skipped[0]['user_id'] == 'USER1'
        assert allocated[0]['user_id'] == 'USER2'
        assert not allocated[0].get('partial'), "Should be full member, not partial"
    
    def test_zero_points_members_ignored(self):
        """Test that 0-point members are handled correctly."""
        members = [
            {'user_id': 'USER1', 'name': 'User 1', 'points': 1.0},
            {'user_id': 'USER2', 'name': 'User 2', 'points': 0.0},  # Inactive/invalid
            {'user_id': 'USER3', 'name': 'User 3', 'points': 1.0},
        ]
        
        allocated, surplus, skipped = split_leg_members_incremental(members, skip_points=0, allocate_points=2.0)
        
        # USER2 with 0 points should be consumed immediately
        total_allocated = sum(m['points'] for m in allocated)
        assert total_allocated == 2.0, "Should allocate 2.0 points total"
    
    def test_small_incremental_requirement_regression(self):
        """
        REGRESSION TEST: Ensure no over-allocation when incremental requirement is smaller
        than member's remaining portion after skip boundary.
        
        Scenario: Member with 1.0 pts straddles skip boundary at 3.0
                 - 0.5 pts consumed by previous tiers (skipped)
                 - 0.5 pts remaining, but THIS tier only needs 0.25 pts (incremental)
                 - Should allocate 0.25 to THIS tier, 0.25 to surplus
        """
        members = [
            {'user_id': 'USER1', 'name': 'User 1', 'points': 2.0},  # Fully skipped
            {'user_id': 'USER2', 'name': 'User 2', 'points': 1.0},  # Partially consumed by previous
            {'user_id': 'USER3', 'name': 'User 3', 'points': 1.0},  # Spans current tier boundary
            {'user_id': 'USER4', 'name': 'User 4', 'points': 1.0},  # Surplus
        ]
        
        # Allocate to a tier with very small incremental requirement
        # skip=3.0 (consumed by lower tiers), allocate=0.25 (tiny incremental)
        allocated, surplus, skipped = split_leg_members_incremental(
            members, skip_points=3.0, allocate_points=0.25
        )
        
        # Verify correct allocation
        total_allocated = sum(m['points'] for m in allocated)
        assert total_allocated == 0.25, f"Should allocate exactly 0.25, got {total_allocated}"
        
        # USER1 fully skipped, USER2 partially skipped
        total_skipped = sum(m['points'] for m in skipped)
        assert total_skipped == 3.0, f"Should skip exactly 3.0, got {total_skipped}"
        
        # Verify USER3 is split correctly
        user3_allocated = [m for m in allocated if m['user_id'] == 'USER3']
        user3_surplus = [m for m in surplus if m['user_id'] == 'USER3']
        
        assert len(user3_allocated) == 1, "USER3 should appear once in allocated"
        assert user3_allocated[0]['points'] == 0.25, "USER3 should contribute 0.25 to THIS tier"
        assert user3_allocated[0].get('partial') == True, "USER3 should be marked partial"
        
        assert len(user3_surplus) == 1, "USER3 should appear once in surplus"
        assert user3_surplus[0]['points'] == 0.75, "USER3 should have 0.75 in surplus"
        assert user3_surplus[0].get('partial') == True, "USER3 surplus should be marked partial"


if __name__ == '__main__':
    # Run tests
    test = TestPartialPointAllocation()
    
    print("Running test suite for partial point allocation...\n")
    
    tests = [
        ('All Platinum - Star Award', test.test_all_platinum_packages_star_award),
        ('All Platinum - Prime Star Award', test.test_all_platinum_packages_prime_star_award),
        ('Mixed Diamond/Platinum - Star Award', test.test_mixed_diamond_platinum_star_award),
        ('Partial Consumption Across Boundaries', test.test_partial_consumption_across_boundaries),
        ('No Double Counting', test.test_no_double_counting),
        ('Edge Case - Exact Boundary', test.test_edge_case_exact_boundary),
        ('Zero Points Members', test.test_zero_points_members_ignored),
        ('Small Incremental Requirement (Regression)', test.test_small_incremental_requirement_regression),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"✅ PASSED: {test_name}")
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {test_name}")
            print(f"   Error: {e}\n")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {test_name}")
            print(f"   Error: {e}\n")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Test Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
