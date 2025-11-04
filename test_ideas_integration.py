#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify Ideas flow integration
This script checks if all the necessary components are in place for the Ideas feature
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test if all necessary modules can be imported"""
    print("Testing imports...")
    
    try:
        from src.handlers.ideas import show_ideas_menu, ideas_router, ideas_text_input
        print("✅ Ideas handlers imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import ideas handlers: {e}")
        return False
    
    try:
        from src.ideas_templates import IDEAS_CATEGORIES, IDEAS_TEMPLATES
        print("✅ Ideas templates imported successfully")
        print(f"   - Found {len(IDEAS_CATEGORIES)} categories")
        print(f"   - Found {len(IDEAS_TEMPLATES)} templates")
    except ImportError as e:
        print(f"❌ Failed to import ideas templates: {e}")
        return False
    
    try:
        from src.translations import t
        print("✅ Translation function imported successfully")
        # Test a few translation keys
        test_keys = ['ideas_menu_title', 'ideas_category_self_motivation', 'idea_morning_motivation_title']
        for key in test_keys:
            result_en = t('en', key)
            result_ru = t('ru', key)
            if result_en != key and result_ru != key:
                print(f"   - Translation key '{key}' exists in both languages")
            else:
                print(f"   - ⚠️  Translation key '{key}' might be missing")
    except ImportError as e:
        print(f"❌ Failed to import translation function: {e}")
        return False
    
    try:
        from src.config import SELECTING_IDEAS_CATEGORY, SELECTING_IDEA_TEMPLATE, EDITING_IDEA_CONTENT
        print("✅ Ideas conversation states imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import ideas conversation states: {e}")
        return False
    
    return True


def test_main_menu_integration():
    """Test if main menu has ideas button"""
    print("\nTesting main menu integration...")
    
    try:
        from src.handlers.main_menu import get_main_menu_keyboard
        from src.translations import t
        
        # Test keyboard generation
        keyboard = get_main_menu_keyboard('en')
        keyboard_text = str(keyboard)
        
        if 'ideas' in keyboard_text.lower():
            print("✅ Ideas button found in main menu")
            return True
        else:
            print("❌ Ideas button not found in main menu")
            return False
            
    except Exception as e:
        print(f"❌ Error testing main menu: {e}")
        return False


def test_conversation_states():
    """Test if conversation states are properly defined"""
    print("\nTesting conversation states...")
    
    try:
        from src.config import (
            SELECTING_IDEAS_CATEGORY, 
            SELECTING_IDEA_TEMPLATE, 
            EDITING_IDEA_CONTENT
        )
        
        states = {
            'SELECTING_IDEAS_CATEGORY': SELECTING_IDEAS_CATEGORY,
            'SELECTING_IDEA_TEMPLATE': SELECTING_IDEA_TEMPLATE,
            'EDITING_IDEA_CONTENT': EDITING_IDEA_CONTENT
        }
        
        # Check if states are unique integers
        values = list(states.values())
        if len(set(values)) == len(values) and all(isinstance(v, int) for v in values):
            print("✅ All ideas conversation states are properly defined")
            for name, value in states.items():
                print(f"   - {name}: {value}")
            return True
        else:
            print("❌ Ideas conversation states have conflicts")
            return False
            
    except Exception as e:
        print(f"❌ Error testing conversation states: {e}")
        return False


def test_create_capsule_integration():
    """Test if create_capsule handler can handle prefill data"""
    print("\nTesting create capsule integration...")
    
    try:
        # Check if create_capsule.py has prefill logic
        with open('src/handlers/create_capsule.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        prefill_indicators = [
            'prefill_text',
            'prefill_content_type',
            'prefill_recipient',
            'prefill_delivery_iso'
        ]
        
        found_indicators = []
        for indicator in prefill_indicators:
            if indicator in content:
                found_indicators.append(indicator)
        
        if len(found_indicators) >= 3:
            print("✅ Create capsule handler has prefill integration")
            print(f"   - Found prefill indicators: {', '.join(found_indicators)}")
            return True
        else:
            print("❌ Create capsule handler missing prefill integration")
            print(f"   - Found only: {', '.join(found_indicators)}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing create capsule integration: {e}")
        return False


def test_sample_idea_generation():
    """Test if we can generate a sample idea"""
    print("\nTesting sample idea generation...")
    
    try:
        from src.ideas_templates import IDEAS_CATEGORIES, IDEAS_TEMPLATES, _compute_delivery
        from src.translations import t
        
        # Get first category and first idea
        first_category = list(IDEAS_CATEGORIES.keys())[0]
        first_idea_key = IDEAS_CATEGORIES[first_category]['ideas'][0]
        template = IDEAS_TEMPLATES[first_idea_key]
        
        # Generate sample content
        title = t('en', template['title_key'])
        text = t('en', template['text_key'])
        hints = t('en', template['hints_key'])
        
        print(f"✅ Successfully generated sample idea:")
        print(f"   - Category: {first_category}")
        print(f"   - Template: {first_idea_key}")
        print(f"   - Title: {title}")
        print(f"   - Text length: {len(text)} chars")
        print(f"   - Hints length: {len(hints)} chars")
        
        # Test delivery time computation
        delivery_preset = template.get('delivery_preset')
        if delivery_preset:
            from src.ideas_templates import dt_in_days, next_new_year
            # Import the compute function properly
            from src.handlers.ideas import _compute_delivery
            delivery_time = _compute_delivery(delivery_preset)
            print(f"   - Computed delivery time: {delivery_time}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating sample idea: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Digital Time Capsule - Ideas Integration Test")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_main_menu_integration,
        test_conversation_states,
        test_create_capsule_integration,
        test_sample_idea_generation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Ideas integration should work correctly.")
        print("\n📝 Next steps:")
        print("   1. Start the bot: python main.py")
        print("   2. Send /start to the bot")
        print("   3. Click the '💡 Ideas' button")
        print("   4. Navigate through categories and templates")
        print("   5. Try editing text and creating a capsule")
    else:
        print(f"❌ {total - passed} test(s) failed. Please fix the issues above.")
    
    print("=" * 60)
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)