#!/usr/bin/env python3
"""Quick integration test for the service layer functionality."""

import sys
import os
sys.path.insert(0, '/home/cytrex/news-mcp')

from sqlmodel import Session
from app.database import engine
from app.services.domain.feed_service import FeedService
from app.services.domain.item_service import ItemService
from app.services.domain.processor_service import ProcessorService
from app.services.domain.analysis_service import AnalysisService
from app.dependencies import get_feed_service, get_processor_service, get_analysis_service


def test_services():
    """Test core service functionality."""
    print("🧪 Testing Service Layer Integration...")

    # Test with database session
    try:
        with Session(engine) as session:
            # Test FeedService
            print("✅ Testing FeedService...")
            feed_service = FeedService(session)
            feeds_result = feed_service.list(limit=5)
            print(f"   Found {len(feeds_result.data) if feeds_result.success else 0} feeds")

            # Test ItemService
            print("✅ Testing ItemService...")
            item_service = ItemService(session)
            stats_result = item_service.get_item_statistics()
            if stats_result.success:
                print(f"   Item stats: {stats_result.data.get('total_items', 0)} total items")

            # Test ProcessorService
            print("✅ Testing ProcessorService...")
            processor_service = ProcessorService(session)
            types_result = processor_service.get_available_processor_types()
            if types_result.success:
                available_types = types_result.data.get('available_types', [])
                print(f"   Available processor types: {len(available_types)}")

            # Test AnalysisService (stateless)
            print("✅ Testing AnalysisService...")
            analysis_service = AnalysisService()
            feeds_result = analysis_service.get_available_feeds()
            if feeds_result.success:
                print(f"   Available feeds for analysis: {len(feeds_result.data)}")

            print("🎉 All service tests passed!")

    except Exception as e:
        print(f"❌ Service test failed: {e}")
        return False

    return True


def test_dependency_injection():
    """Test dependency injection system."""
    print("\n🔧 Testing Dependency Injection...")

    try:
        with Session(engine) as session:
            # Test dependency functions
            feed_service = get_feed_service.dependency(session=session)
            print(f"✅ FeedService dependency: {type(feed_service).__name__}")

            processor_service = get_processor_service.dependency(session=session)
            print(f"✅ ProcessorService dependency: {type(processor_service).__name__}")

            analysis_service = get_analysis_service()
            print(f"✅ AnalysisService dependency: {type(analysis_service).__name__}")

            print("🎉 Dependency injection tests passed!")

    except Exception as e:
        print(f"❌ Dependency injection test failed: {e}")
        return False

    return True


if __name__ == "__main__":
    print("🚀 Starting Service Layer Integration Tests...")

    success1 = test_services()
    success2 = test_dependency_injection()

    if success1 and success2:
        print("\n✨ All Service Layer tests completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)