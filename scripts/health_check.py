#!/usr/bin/env python3
"""
416Homes Scraper Health Check Script

Tests all scrapers for functionality and performance.
Reports failures via email and GitHub issues.
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any
import json
import aiohttp
import re
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScraperHealthCheck:
    """Health checker for all 416Homes scrapers"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.results = {
            'realtor_ca': {'status': 'unknown', 'response_time': 0, 'listings_count': 0, 'error': None},
            'kijiji': {'status': 'unknown', 'response_time': 0, 'listings_count': 0, 'error': None},
            'redfin': {'status': 'unknown', 'response_time': 0, 'listings_count': 0, 'error': None},
            'zoocasa': {'status': 'unknown', 'response_time': 0, 'listings_count': 0, 'error': None},
            'housesigma': {'status': 'unknown', 'response_time': 0, 'listings_count': 0, 'error': None}
        }
        self.start_time = time.time()
    
    async def test_api_health(self) -> bool:
        """Test if API is responding"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health", timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"API Health Check: {data.get('status', 'unknown')}")
                        return True
                    else:
                        logger.error(f"API Health Check failed: HTTP {response.status}")
                        return False
        except Exception as e:
            logger.error(f"API Health Check error: {e}")
            return False
    
    async def test_scraper(self, source: str, area: str = "toronto") -> Dict[str, Any]:
        """Test individual scraper with timeout and error handling"""
        
        start_time = time.time()
        
        try:
            # Test scraper endpoint
            url = f"{self.base_url}/listings?city={area}&limit=5&source={source}"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                headers = {
                    'User-Agent': '416Homes-Health-Check/1.0',
                    'Accept': 'application/json'
                }
                
                async with session.get(url, headers=headers) as response:
                    response_time = round((time.time() - start_time) * 1000)  # Convert to ms
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            listings_count = len(data) if isinstance(data, list) else 0
                            
                            # Validate listing structure
                            if listings_count > 0:
                                sample_listing = data[0]
                                required_fields = ['id', 'address', 'price', 'bedrooms', 'bathrooms', 'source', 'url']
                                
                                missing_fields = [field for field in required_fields if field not in sample_listing]
                                
                                if missing_fields:
                                    error_msg = f"Missing fields: {', '.join(missing_fields)}"
                                    logger.error(f"{source} scraper validation failed: {error_msg}")
                                    return {
                                        'status': 'failed',
                                        'response_time': response_time,
                                        'listings_count': listings_count,
                                        'error': error_msg
                                    }
                                
                                # Check for reasonable values
                                if not isinstance(sample_listing.get('price'), (int, float)) or sample_listing['price'] <= 0:
                                    error_msg = f"Invalid price value: {sample_listing.get('price')}"
                                    logger.error(f"{source} scraper validation failed: {error_msg}")
                                    return {
                                        'status': 'failed',
                                        'response_time': response_time,
                                        'listings_count': listings_count,
                                        'error': error_msg
                                    }
                                
                                logger.info(f"{source} scraper: OK - {listings_count} listings in {response_time}ms")
                                return {
                                    'status': 'success',
                                    'response_time': response_time,
                                    'listings_count': listings_count,
                                    'error': None
                                }
                                
                            elif response.status == 200:
                                logger.warning(f"{source} scraper: No listings returned (empty)")
                                return {
                                    'status': 'success',
                                    'response_time': response_time,
                                    'listings_count': 0,
                                    'error': None
                                }
                            else:
                                error_msg = f"HTTP {response.status}"
                                logger.error(f"{source} scraper failed: {error_msg}")
                                return {
                                    'status': 'failed',
                                    'response_time': response_time,
                                    'listings_count': 0,
                                    'error': error_msg
                                }
                                
                        except json.JSONDecodeError as e:
                            error_msg = f"Invalid JSON response: {str(e)}"
                            logger.error(f"{source} scraper failed: {error_msg}")
                            return {
                                'status': 'failed',
                                'response_time': response_time,
                                'listings_count': 0,
                                'error': error_msg
                            }
                            
        except asyncio.TimeoutError:
            error_msg = "Request timeout (30s)"
            logger.error(f"{source} scraper failed: {error_msg}")
            return {
                'status': 'failed',
                'response_time': 30000,
                'listings_count': 0,
                'error': error_msg
            }
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"{source} scraper failed: {error_msg}")
            return {
                'status': 'failed',
                'response_time': 0,
                'listings_count': 0,
                'error': error_msg
            }
    
    async def test_valuation_endpoint(self) -> Dict[str, Any]:
        """Test property valuation endpoint"""
        
        start_time = time.time()
        
        try:
            test_data = {
                "neighbourhood": "King West",
                "property_type": "Condo Apt",
                "city": "Toronto",
                "bedrooms": 2,
                "bathrooms": 2,
                "sqft": 950,
                "list_price": 899000
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                headers = {
                    'Content-Type': 'application/json',
                    'User-Agent': '416Homes-Health-Check/1.0'
                }
                
                async with session.post(f"{self.base_url}/valuate", json=test_data, headers=headers) as response:
                    response_time = round((time.time() - start_time) * 1000)
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            
                            # Validate valuation response
                            required_fields = ['estimated_value', 'confidence', 'market_analysis']
                            missing_fields = [field for field in required_fields if field not in data]
                            
                            if missing_fields:
                                error_msg = f"Missing fields: {', '.join(missing_fields)}"
                                logger.error(f"Valuation endpoint validation failed: {error_msg}")
                                return {
                                    'status': 'failed',
                                    'response_time': response_time,
                                    'error': error_msg
                                }
                            
                            # Check for reasonable values
                            if not isinstance(data.get('estimated_value'), (int, float)) or data['estimated_value'] <= 0:
                                error_msg = f"Invalid estimated value: {data.get('estimated_value')}"
                                logger.error(f"Valuation endpoint validation failed: {error_msg}")
                                return {
                                    'status': 'failed',
                                    'response_time': response_time,
                                    'error': error_msg
                                }
                            
                            logger.info(f"Valuation endpoint: OK - ${data.get('estimated_value', 0):,} in {response_time}ms")
                            return {
                                'status': 'success',
                                'response_time': response_time,
                                'error': None
                            }
                            
                        except json.JSONDecodeError as e:
                            error_msg = f"Invalid JSON response: {str(e)}"
                            logger.error(f"Valuation endpoint failed: {error_msg}")
                            return {
                                'status': 'failed',
                                'response_time': response_time,
                                'error': error_msg
                            }
                    else:
                        error_msg = f"HTTP {response.status}"
                        logger.error(f"Valuation endpoint failed: {error_msg}")
                        return {
                            'status': 'failed',
                            'response_time': response_time,
                            'error': error_msg
                        }
                        
        except asyncio.TimeoutError:
            error_msg = "Request timeout (30s)"
            logger.error(f"Valuation endpoint failed: {error_msg}")
            return {
                'status': 'failed',
                'response_time': 30000,
                'error': error_msg
            }
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Valuation endpoint failed: {error_msg}")
            return {
                'status': 'failed',
                'response_time': 0,
                'error': error_msg
            }
    
    async def test_video_job_endpoint(self) -> Dict[str, Any]:
        """Test video job creation endpoint"""
        
        start_time = time.time()
        
        try:
            test_data = {
                "listing_url": "https://www.realtor.ca/test-listing",
                "customer_email": "health-check@416homes.ca"
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                headers = {
                    'Content-Type': 'application/json',
                    'User-Agent': '416Homes-Health-Check/1.0'
                }
                
                async with session.post(f"{self.base_url}/video-jobs", json=test_data, headers=headers) as response:
                    response_time = round((time.time() - start_time) * 1000)
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            
                            # Validate video job response
                            required_fields = ['id', 'status', 'message']
                            missing_fields = [field for field in required_fields if field not in data]
                            
                            if missing_fields:
                                error_msg = f"Missing fields: {', '.join(missing_fields)}"
                                logger.error(f"Video job endpoint validation failed: {error_msg}")
                                return {
                                    'status': 'failed',
                                    'response_time': response_time,
                                    'error': error_msg
                                }
                            
                            logger.info(f"Video job endpoint: OK - job {data.get('id', 'unknown')} in {response_time}ms")
                            return {
                                'status': 'success',
                                'response_time': response_time,
                                'error': None
                            }
                            
                        except json.JSONDecodeError as e:
                            error_msg = f"Invalid JSON response: {str(e)}"
                            logger.error(f"Video job endpoint failed: {error_msg}")
                            return {
                                'status': 'failed',
                                'response_time': response_time,
                                'error': error_msg
                            }
                    else:
                        error_msg = f"HTTP {response.status}"
                        logger.error(f"Video job endpoint failed: {error_msg}")
                        return {
                            'status': 'failed',
                            'response_time': response_time,
                            'error': error_msg
                        }
                        
        except asyncio.TimeoutError:
            error_msg = "Request timeout (30s)"
            logger.error(f"Video job endpoint failed: {error_msg}")
            return {
                'status': 'failed',
                'response_time': 30000,
                'error': error_msg
            }
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Video job endpoint failed: {error_msg}")
            return {
                'status': 'failed',
                'response_time': 0,
                'error': error_msg
            }
    
    def calculate_overall_health(self) -> str:
        """Calculate overall health status"""
        
        total_checks = 0
        passed_checks = 0
        failed_checks = 0
        
        for source, result in self.results.items():
            total_checks += 1
            if result['status'] == 'success':
                passed_checks += 1
            elif result['status'] == 'failed':
                failed_checks += 1
        
        if failed_checks > 0:
            return 'CRITICAL'
        elif failed_checks > 1:
            return 'DEGRADED'
        elif passed_checks == total_checks:
            return 'HEALTHY'
        else:
            return 'WARNING'
    
    def generate_health_report(self) -> str:
        """Generate detailed health report"""
        
        report = []
        report.append("=" * 60)
        report.append("416HOMES SCRAPER HEALTH CHECK REPORT")
        report.append("=" * 60)
        report.append(f"Timestamp: {datetime.utcnow().isoformat()}")
        report.append(f"Total Duration: {round((time.time() - self.start_time) * 1000)}ms")
        report.append("")
        
        # API Health
        api_healthy = asyncio.get_event_loop().run_until_complete(
            self.test_api_health(),
            timeout=15
        )
        report.append(f"API Health: {'✅ PASS' if api_healthy else '❌ FAIL'}")
        
        # Individual Scrapers
        scrapers = ['realtor_ca', 'kijiji', 'redfin', 'zoocasa']
        for scraper in scrapers:
            result = self.results[scraper]
            status_icon = "✅" if result['status'] == 'success' else "❌"
            time_info = f" ({result['response_time']}ms)" if result['response_time'] > 0 else ""
            error_info = f" - {result['error']}" if result['error'] else ""
            
            report.append(f"{scraper}: {status_icon}{time_info}{error_info}")
            if result['status'] == 'success':
                report.append(f"  Listings: {result['listings_count']}")
        
        report.append("")
        
        # Valuation Endpoint
        valuation_result = asyncio.get_event_loop().run_until_complete(
            self.test_valuation_endpoint(),
            timeout=15
        )
        val_status_icon = "✅" if valuation_result['status'] == 'success' else "❌"
        val_time_info = f" ({valuation_result['response_time']}ms)" if valuation_result['response_time'] > 0 else ""
        val_error_info = f" - {valuation_result['error']}" if valuation_result['error'] else ""
        
        report.append(f"Valuation: {val_status_icon}{val_time_info}{val_error_info}")
        
        # Video Job Endpoint
        video_result = asyncio.get_event_loop().run_until_complete(
            self.test_video_job_endpoint(),
            timeout=15
        )
        video_status_icon = "✅" if video_result['status'] == 'success' else "❌"
        video_time_info = f" ({video_result['response_time']}ms)" if video_result['response_time'] > 0 else ""
        video_error_info = f" - {video_result['error']}" if video_result['error'] else ""
        
        report.append(f"Video Jobs: {video_status_icon}{video_time_info}{video_error_info}")
        
        report.append("")
        
        # Overall Status
        overall_status = self.calculate_overall_health()
        status_icons = {
            'HEALTHY': '🟢',
            'WARNING': '🟡', 
            'DEGRADED': '🔴',
            'CRITICAL': '🔴'
        }
        
        report.append(f"Overall Status: {status_icons.get(overall_status, '❓')} {overall_status}")
        
        # Recommendations
        report.append("")
        report.append("RECOMMENDATIONS:")
        
        failed_scrapers = [s for s, r in self.results.items() if r['status'] == 'failed']
        if failed_scrapers:
            report.append(f"• Failed scrapers: {', '.join(failed_scrapers)}")
            report.append("• Check CSS selectors for changes on target websites")
            report.append("• Test scrapers manually: python -m scraper.run_all --source <source> --area toronto")
        
        if not api_healthy:
            report.append("• API server is not responding - check server status")
        
        if valuation_result['status'] == 'failed':
            report.append("• Valuation endpoint issues - check ML model and API")
        
        if video_result['status'] == 'failed':
            report.append("• Video job creation issues - check pipeline and database")
        
        report.append("")
        report.append("NEXT CHECK: Run in 6 hours or trigger manually via GitHub Actions")
        
        return "\n".join(report)
    
    async def run_all_checks(self):
        """Run all health checks"""
        
        logger.info("Starting 416Homes scraper health check...")
        
        # Test API first
        api_healthy = await self.test_api_health()
        if not api_healthy:
            logger.error("API is not healthy - aborting scraper tests")
            return False
        
        # Test all scrapers concurrently
        scraper_tasks = [
            self.test_scraper('realtor_ca'),
            self.test_scraper('kijiji'),
            self.test_scraper('redfin'),
            self.test_scraper('zoocasa')
        ]
        
        scraper_results = await asyncio.gather(*scraper_tasks, return_exceptions=True)
        
        for i, result in enumerate(scraper_results):
            source = ['realtor_ca', 'kijiji', 'redfin', 'zoocasa'][i]
            if isinstance(result, Exception):
                logger.error(f"Exception testing {source}: {result}")
                self.results[source] = {
                    'status': 'failed',
                    'response_time': 0,
                    'listings_count': 0,
                    'error': f"Exception: {str(result)}"
                }
            else:
                self.results[source] = result
        
        # Test valuation and video endpoints
        valuation_result = await self.test_valuation_endpoint()
        self.results['valuation'] = valuation_result
        
        video_result = await self.test_video_job_endpoint()
        self.results['video_jobs'] = video_result
        
        # Generate and log report
        report = self.generate_health_report()
        logger.info("Health check completed:\n" + report)
        
        # Print report for GitHub Actions
        print(report)
        
        # Determine exit code
        overall_status = self.calculate_overall_health()
        if overall_status in ['CRITICAL', 'DEGRADED']:
            logger.error("Health check completed with critical failures")
            sys.exit(1)
        elif overall_status == 'WARNING':
            logger.warning("Health check completed with warnings")
            sys.exit(0)
        else:
            logger.info("Health check completed successfully")
            sys.exit(0)

async def main():
    """Main entry point"""
    checker = ScraperHealthCheck()
    await checker.run_all_checks()

if __name__ == "__main__":
    asyncio.run(main())
