"""Tests for ReconciliationClient against a running reconciliation service.

Run these tests with:
    uv run pytest backend/tests/integration/test_reconciliation_client.py -m integration
Exclude marked integration tests with:
    uv run pytest backend/tests -m "not integration"
"""

import socket
import subprocess

import httpx
import pytest

from backend.app.clients.reconciliation_client import ReconciliationClient, ReconciliationQuery

# pylint: disable=redefined-outer-name


class TestReconciliationClientIntegration:
    """Tests that make live requests to the reconciliation service on localhost:8000."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_connection_to_port_8000(self):
        """Test that client can attempt connection to OpenRefine service on port 8000."""
        client = ReconciliationClient(base_url="http://localhost:8000")

        # Test health check endpoint
        health_result = await client.check_health()

        # Verify the client is configured for port 8000
        assert client.base_url == "http://localhost:8000"
        assert "status" in health_result
        assert "service_url" in health_result
        assert health_result["service_url"] == "http://localhost:8000"

        # Status can be either "online" or "offline" depending on whether service is running
        assert health_result["status"] in ["online", "offline"]

        # If offline, should have error message
        if health_result["status"] == "offline":
            assert "error" in health_result
        # If online, should have service name
        else:
            assert "service_name" in health_result

        await client.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_live_health_check(self):
        """Test health check against live service on port 8000.

        This test attempts to connect to the actual service and reports detailed
        connection information. Check logs/endpoint_errors.log for [RECON] traces.
        """
        client = ReconciliationClient(base_url="http://localhost:8000", timeout=10.0)

        print("\n=== Testing Health Check ===")
        print(f"Target: {client.base_url}/reconcile")
        print(f"Timeout: {client.timeout}s")

        try:
            health = await client.check_health()

            print("\nHealth Check Result:")
            print(f"  Status: {health['status']}")
            print(f"  Service URL: {health['service_url']}")

            if health["status"] == "online":
                print(f"  Service Name: {health['service_name']}")
                assert health["service_name"] is not None
                print("\n✓ Service is ONLINE")
            else:
                print(f"  Error: {health.get('error', 'Unknown')}")
                print("\n✗ Service is OFFLINE")
                print("\nTroubleshooting:")
                print("  1. Verify service is running: docker ps | grep reconcile")
                print("  2. Check service logs: docker logs <container_id>")
                print("  3. Verify port mapping: docker port <container_id>")
                print("  4. Test direct connection: curl http://localhost:8000/reconcile")

            assert "status" in health

        except Exception as e:
            print(f"\n✗ Unexpected error: {type(e).__name__}: {e}")
            raise
        finally:
            await client.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_live_service_manifest(self):
        """Test getting service manifest from live service.

        Retrieves actual service metadata including supported entity types.
        """
        client = ReconciliationClient(base_url="http://localhost:8000", timeout=10.0)

        print("\n=== Testing Service Manifest ===")

        try:
            manifest = await client.get_service_manifest()

            print("\nManifest Retrieved:")
            print(f"  Service Name: {manifest.get('name', 'N/A')}")
            print(f"  Identifier Space: {manifest.get('identifierSpace', 'N/A')}")
            print(f"  Schema Space: {manifest.get('schemaSpace', 'N/A')}")

            if "defaultTypes" in manifest:
                print(f"\n  Supported Types ({len(manifest['defaultTypes'])}):")
                for entity_type in manifest["defaultTypes"][:5]:  # Show first 5
                    print(f"    - {entity_type.get('id', 'N/A')}: {entity_type.get('name', 'N/A')}")
                if len(manifest["defaultTypes"]) > 5:
                    print(f"    ... and {len(manifest['defaultTypes']) - 5} more")

            assert "name" in manifest
            print("\n✓ Service manifest retrieved successfully")

        except httpx.ConnectError as e:
            print(f"\n✗ Connection failed: {e}")
            print("\nService appears to be offline or unreachable")
            pytest.skip("Service not running")
        except Exception as e:
            print(f"\n✗ Error: {type(e).__name__}: {e}")
            raise
        finally:
            await client.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_live_reconcile_batch_single_query(self):
        """Test batch reconciliation with a single query against live service.

        Sends an actual reconciliation query to test the full request/response cycle.
        """
        client = ReconciliationClient(base_url="http://localhost:8000", timeout=10.0)

        print("\n=== Testing Batch Reconciliation ===")

        # Simple test query
        queries = {"q0": ReconciliationQuery(query="Test Site", entity_type="site", limit=3)}

        print(f"\nQuery: '{queries['q0'].query}'")
        print(f"Type: {queries['q0'].type}")
        print(f"Limit: {queries['q0'].limit}")

        try:
            result = await client.reconcile_batch(queries)

            print("\nReconciliation Result:")
            print(f"  Queries processed: {len(result)}")

            if "q0" in result:
                candidates = result["q0"]
                print(f"  Candidates found: {len(candidates)}")

                for i, candidate in enumerate(candidates[:3], 1):  # Show first 3
                    print(f"\n  Candidate {i}:")
                    print(f"    ID: {candidate.id}")
                    print(f"    Name: {candidate.name}")
                    print(f"    Score: {candidate.score}")
                    print(f"    Match: {candidate.match}")

            assert "q0" in result
            print("\n✓ Batch reconciliation completed successfully")

        except httpx.ConnectError as e:
            print(f"\n✗ Connection failed: {e}")
            print("\nCheck logs/endpoint_errors.log for [RECON] traces")
            pytest.skip("Service not running")
        except Exception as e:
            print(f"\n✗ Error: {type(e).__name__}: {e}")
            raise
        finally:
            await client.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_live_suggest_entities(self):
        """Test entity suggestions against live service.

        Tests autocomplete functionality with a simple prefix query.
        """
        client = ReconciliationClient(base_url="http://localhost:8000", timeout=10.0)

        print("\n=== Testing Entity Suggestions ===")

        prefix = "Site"
        print(f"\nPrefix: '{prefix}'")
        print("Limit: 5")

        try:
            suggestions = await client.suggest_entities(prefix=prefix, limit=5)

            print(f"\nSuggestions Retrieved: {len(suggestions)}")

            for i, suggestion in enumerate(suggestions, 1):
                print(f"\n  Suggestion {i}:")
                print(f"    ID: {suggestion.id}")
                print(f"    Name: {suggestion.name}")
                print(f"    Score: {suggestion.score}")

            print("\n✓ Entity suggestions retrieved successfully")

        except httpx.ConnectError as e:
            print(f"\n✗ Connection failed: {e}")
            pytest.skip("Service not running")
        except Exception as e:
            print(f"\n✗ Error: {type(e).__name__}: {e}")
            raise
        finally:
            await client.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_live_connection_diagnostics(self):
        """Comprehensive connection diagnostics test.

        Performs multiple checks to diagnose connection issues:
        - Docker container port mapping check
        - DNS resolution
        - TCP connection
        - HTTP handshake
        - Service response

        This test provides detailed output for debugging connection problems.
        """

        print("\n=== Connection Diagnostics ===")

        host = "localhost"
        port = 8000
        timeout = 5.0

        # Test 0: Docker Port Mapping Check
        print("\n0. Docker Port Mapping Check:")
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.ID}}|{{.Image}}|{{.Ports}}"], capture_output=True, text=True, timeout=5, check=True
            )

            if result.returncode == 0:
                found_mapping = False
                found_container = False

                for line in result.stdout.strip().split("\n"):
                    if not line:
                        continue
                    parts = line.split("|")
                    if len(parts) >= 3:
                        container_id, image, ports = parts[0], parts[1], parts[2]

                        # Check if port 8000 is mentioned
                        if "8000" in ports or "reconcile" in image.lower() or "openrefine" in image.lower():
                            found_container = True
                            print(f"\n   Container: {container_id[:12]}")
                            print(f"   Image: {image}")
                            print(f"   Ports: {ports}")

                            # Check if properly mapped to host
                            if "0.0.0.0:8000->8000" in ports or f"{host}:8000->8000" in ports:
                                found_mapping = True
                                print("   ✓ Port 8000 is MAPPED to host")
                            elif "8000/tcp" in ports and "->" not in ports:
                                print("   ✗ Port 8000 is EXPOSED but NOT MAPPED to host!")
                                print("\n   PROBLEM FOUND: Container has port 8000 but it's not published to host")
                                print("   Solution: Add port mapping when starting container:")
                                print("     docker run -p 8000:8000 ...")
                                print("   Or in docker-compose.yml:")
                                print("     ports:")
                                print('       - "8000:8000"')

                if not found_container:
                    print("   ⚠ No containers found with port 8000 or reconciliation service")
                elif not found_mapping:
                    print("\n   ⚠ WARNING: Container found but port not mapped to host")
                    pytest.skip("Docker port 8000 not mapped to host - see diagnostics above")

        except FileNotFoundError:
            print("   ⚠ Docker CLI not available, skipping container check")
        except Exception as e:  # pylint: disable=broad-except
            print(f"   ⚠ Could not check Docker containers: {e}")

        # Test 1: DNS Resolution
        print(f"\n1. DNS Resolution for '{host}':")
        try:
            ip_address = socket.gethostbyname(host)
            print(f"   ✓ Resolved to: {ip_address}")
        except socket.gaierror as e:
            print(f"   ✗ DNS resolution failed: {e}")
            pytest.fail(f"DNS resolution failed: {e}")

        # Test 2: TCP Connection
        print(f"\n2. TCP Connection to {host}:{port}:")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        port_open = False
        try:
            result = sock.connect_ex((host, port))
            if result == 0:
                print(f"   ✓ Port {port} is OPEN on host")
                port_open = True
            else:
                print(f"   ✗ Port {port} is CLOSED on host (error code: {result})")
                print("\n   Common causes:")
                print("   - Service running in Docker but port not mapped")
                print("   - Service not started")
                print("   - Firewall blocking connection")
                print("\n   Debug commands:")
                print(f"   - Check host port: lsof -i :{port}")
                print("   - Check Docker: docker ps --format '{{.Ports}}'")
                print("   - Check container logs: docker logs <container_id>")
                pytest.skip(f"Port {port} is not reachable on host")
        except socket.timeout:
            print(f"   ✗ Connection timeout after {timeout}s")
            pytest.skip("Connection timeout")
        except Exception as e:  # pylint: disable=broad-except
            print(f"   ✗ Connection error: {e}")
            pytest.skip(f"Connection error: {e}")
        finally:
            sock.close()

        # Test 3: HTTP Health Check
        if port_open:
            print("\n3. HTTP Health Check:")
            client = ReconciliationClient(base_url=f"http://{host}:{port}", timeout=timeout)
            try:
                health = await client.check_health()

                if health["status"] == "online":
                    print("   ✓ Service is ONLINE")
                    print(f"   ✓ Service Name: {health.get('service_name', 'Unknown')}")
                else:
                    print("   ✗ Service is OFFLINE")
                    print(f"   Error: {health.get('error', 'Unknown')}")

            except Exception as e:  # pylint: disable=broad-except
                print(f"   ✗ Health check failed: {type(e).__name__}: {e}")
            finally:
                await client.close()

        print("\n=== Diagnostics Complete ===")
        print("\nFor detailed traces, check:")
        print("  logs/endpoint_errors.log | grep '[RECON]'")
