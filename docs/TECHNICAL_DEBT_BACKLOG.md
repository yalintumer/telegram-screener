# 📋 Technical Debt Backlog (JIRA Format)

**Project:** telegram-screener  
**Sprint Duration:** 4 weeks  
**Release Cadence:** Weekly (her hafta sonu releaseable)  
**Current State:** 163 tests, 50% coverage, production'da çalışıyor

---

## 📊 Current Coverage Analysis

| Module | Coverage | Priority | Effort |
|--------|----------|----------|--------|
| analytics.py | 23% | HIGH | M |
| cache.py | 19% | HIGH | S |
| signal_tracker.py | 14% | HIGH | M |
| notion_client.py | 12% | MEDIUM | L |
| data_source_alpha_vantage.py | 2% | LOW | S |
| filters.py | 66% | MEDIUM | S |
| scanner.py | 58% | MEDIUM | M |
| data_source_yfinance.py | 40% | MEDIUM | S |
| telegram_client.py | 70% | LOW | S |

---

# 🎯 EPIC-001: Test Coverage Improvement

**Goal:** Coverage 50% → 75%  
**Timeline:** Week 1-2  
**Business Value:** Production stability, safe refactoring  

---

## STORY-001: Analytics Module Testing
**Epic:** EPIC-001  
**Priority:** P1 - Critical  
**Estimate:** M (4-6 hours)  
**Sprint:** Week 1  

### Description
`analytics.py` (83 statements, 23% coverage) provides signal tracking metrics. Untested code risks silent failures in performance reporting.

### Acceptance Criteria
- [ ] Coverage: 23% → 80%
- [ ] All public methods have unit tests
- [ ] Edge cases: empty data, malformed JSON
- [ ] No production behavior change

### Test Plan
```python
# Test cases:
1. test_calculate_metrics_empty_signals
2. test_calculate_metrics_with_performance_data  
3. test_format_summary_output
4. test_track_signal_called_signals
5. test_error_handling_invalid_data
```

### Files to Modify
- `tests/test_analytics.py` (CREATE)
- `src/analytics.py` (READ ONLY - no changes)

### Dependencies
- None (isolated module)

### Risk Assessment
- **Risk Level:** LOW
- **Rollback:** Delete test file
- **Production Impact:** None (test-only changes)

---

## STORY-002: Cache Module Testing
**Epic:** EPIC-001  
**Priority:** P1 - Critical  
**Estimate:** S (2-3 hours)  
**Sprint:** Week 1  

### Description
`cache.py` (67 statements, 19% coverage) handles market cap caching. Critical for performance.

### Acceptance Criteria
- [ ] Coverage: 19% → 85%
- [ ] File I/O operations tested with tmp files
- [ ] TTL expiration logic verified
- [ ] Thread safety if applicable

### Test Plan
```python
# Test cases:
1. test_cache_hit_returns_stored_value
2. test_cache_miss_returns_none
3. test_cache_expiration_after_ttl
4. test_cache_persistence_to_file
5. test_cache_load_from_corrupted_file
6. test_cache_concurrent_access
```

### Files to Modify
- `tests/test_cache.py` (CREATE)

### Dependencies
- None

### Risk Assessment
- **Risk Level:** LOW
- **Rollback:** Delete test file

---

## STORY-003: Signal Tracker Testing
**Epic:** EPIC-001  
**Priority:** P1 - Critical  
**Estimate:** M (4-5 hours)  
**Sprint:** Week 1  

### Description
`signal_tracker.py` (104 statements, 14% coverage) manages signal state and performance tracking. JSON state management is critical.

### Acceptance Criteria
- [ ] Coverage: 14% → 75%
- [ ] JSON load/save tested
- [ ] Signal state transitions verified
- [ ] Performance calculation tested

### Test Plan
```python
# Test cases:
1. test_load_signals_from_file
2. test_save_signals_atomic_write
3. test_add_new_signal
4. test_update_signal_performance
5. test_get_pending_signals
6. test_handle_corrupted_json
```

### Files to Modify
- `tests/test_signal_tracker.py` (CREATE)

### Dependencies
- STORY-002 (cache patterns useful)

### Risk Assessment
- **Risk Level:** LOW
- **Rollback:** Delete test file

---

## STORY-004: Integration Smoke Test
**Epic:** EPIC-001  
**Priority:** P2 - High  
**Estimate:** S (2-3 hours)  
**Sprint:** Week 1  

### Description
Create E2E smoke test that verifies the system can start, load config, and run one scan cycle without errors (with mocked external APIs).

### Acceptance Criteria
- [ ] Test loads config successfully
- [ ] Test initializes all modules
- [ ] Test runs dry-run scan
- [ ] No external API calls (fully mocked)
- [ ] Completes in < 10 seconds

### Test Plan
```python
# Single integration test:
def test_smoke_full_cycle():
    # Mock: Notion, Telegram, yfinance
    # Run: main.main(['--scan-only'])
    # Assert: No exceptions, health.json updated
```

### Files to Modify
- `tests/test_integration.py` (CREATE)

### Dependencies
- STORY-001, STORY-002, STORY-003

### Risk Assessment
- **Risk Level:** LOW
- **Rollback:** Delete test file

---

# 🎯 EPIC-002: Notion Client Reliability

**Goal:** Notion API stability, retry logic, better error handling  
**Timeline:** Week 2  
**Business Value:** Reduced manual intervention, data integrity  

---

## STORY-005: Notion Client Unit Tests
**Epic:** EPIC-002  
**Priority:** P2 - High  
**Estimate:** L (6-8 hours)  
**Sprint:** Week 2  

### Description
`notion_client.py` (553 statements, 12% coverage) is the largest untested module. Needs comprehensive mocking.

### Acceptance Criteria
- [ ] Coverage: 12% → 60%
- [ ] All API methods have mock tests
- [ ] Retry logic verified
- [ ] Error responses handled

### Test Plan
```python
# Key test categories:
1. Query methods (query_database, get_page)
2. Write methods (create_page, update_page)
3. Error handling (rate limits, 4xx, 5xx)
4. Retry behavior verification
```

### Files to Modify
- `tests/test_notion_client.py` (CREATE)

### Dependencies
- Week 1 complete

### Risk Assessment
- **Risk Level:** MEDIUM (large module)
- **Rollback:** Delete test file

---

## STORY-006: Notion Retry Enhancement
**Epic:** EPIC-002  
**Priority:** P2 - High  
**Estimate:** M (3-4 hours)  
**Sprint:** Week 2  

### Description
Add exponential backoff and jitter to Notion API calls. Current retry may hammer API on failures.

### Acceptance Criteria
- [ ] Exponential backoff: 1s, 2s, 4s, 8s
- [ ] Jitter: ±10% randomization
- [ ] Max retries: 5 (configurable)
- [ ] Logging on each retry attempt
- [ ] ADR documenting change

### Test Plan
```python
1. test_retry_backoff_timing
2. test_max_retries_exceeded
3. test_jitter_within_bounds
```

### Files to Modify
- `src/notion_client.py` (modify retry logic)
- `tests/test_notion_client.py` (add tests)
- `docs/adr/ADR-004-notion-retry.md` (CREATE)

### Dependencies
- STORY-005 (tests first)

### Risk Assessment
- **Risk Level:** MEDIUM (behavior change)
- **Rollback:** Revert commit

---

# 🎯 EPIC-003: Data Source Reliability

**Goal:** Stable market data fetching  
**Timeline:** Week 3  
**Business Value:** Accurate signals, fewer false positives  

---

## STORY-007: yfinance Testing
**Epic:** EPIC-003  
**Priority:** P2 - High  
**Estimate:** M (4-5 hours)  
**Sprint:** Week 3  

### Description
`data_source_yfinance.py` (52 statements, 40% coverage) needs better error handling tests.

### Acceptance Criteria
- [ ] Coverage: 40% → 85%
- [ ] Network errors handled
- [ ] Empty/invalid data handled
- [ ] Rate limiting tested

### Files to Modify
- `tests/test_data_source_yfinance.py` (CREATE)

---

## STORY-008: Filters Module Testing
**Epic:** EPIC-003  
**Priority:** P2 - High  
**Estimate:** S (2-3 hours)  
**Sprint:** Week 3  

### Description
`filters.py` (118 statements, 66% coverage) needs edge case coverage.

### Acceptance Criteria
- [ ] Coverage: 66% → 90%
- [ ] Boundary conditions tested
- [ ] Invalid input handling

### Files to Modify
- `tests/test_filters.py` (ENHANCE)

---

## STORY-009: Scanner Module Coverage
**Epic:** EPIC-003  
**Priority:** P2 - High  
**Estimate:** M (4-5 hours)  
**Sprint:** Week 3  

### Description
`scanner.py` (305 statements, 58% coverage) orchestration logic needs more coverage.

### Acceptance Criteria
- [ ] Coverage: 58% → 80%
- [ ] Error propagation tested
- [ ] Partial failure handling

### Files to Modify
- `tests/test_scanner.py` (ENHANCE)

---

# 🎯 EPIC-004: Observability & Documentation

**Goal:** Better monitoring, runbooks, operational docs  
**Timeline:** Week 4  
**Business Value:** Faster incident response, knowledge transfer  

---

## STORY-010: Health Check Enhancement
**Epic:** EPIC-004  
**Priority:** P3 - Medium  
**Estimate:** S (2-3 hours)  
**Sprint:** Week 4  

### Description
Add detailed health metrics: memory usage, last error, API latencies.

### Acceptance Criteria
- [ ] Memory usage in health.json
- [ ] Last 5 errors summary
- [ ] API latency P50/P95
- [ ] Tests for new metrics

### Files to Modify
- `src/health.py`
- `tests/test_health.py`

---

## STORY-011: Operational Runbook
**Epic:** EPIC-004  
**Priority:** P3 - Medium  
**Estimate:** M (3-4 hours)  
**Sprint:** Week 4  

### Description
Create runbook for common operational tasks: restart, rollback, log analysis.

### Acceptance Criteria
- [ ] Incident response checklist
- [ ] Log analysis guide
- [ ] Rollback procedure (< 5 min)
- [ ] Health check interpretation

### Files to Modify
- `docs/RUNBOOK.md` (CREATE)

---

## STORY-012: Monitoring Dashboard Spec
**Epic:** EPIC-004  
**Priority:** P3 - Medium  
**Estimate:** S (2 hours)  
**Sprint:** Week 4  

### Description
Design spec for Grafana/monitoring dashboard (implementation future).

### Acceptance Criteria
- [ ] Key metrics identified
- [ ] Alert thresholds defined
- [ ] Dashboard mockup/spec

### Files to Modify
- `docs/MONITORING_SPEC.md` (CREATE)

---

# 📈 Dependency Graph

```
EPIC-001: Test Coverage
├── STORY-001: analytics tests ──────────┐
├── STORY-002: cache tests ──────────────┼──→ STORY-004: Integration
├── STORY-003: signal_tracker tests ─────┘
└── STORY-004: Integration smoke test

EPIC-002: Notion Reliability  
├── STORY-005: notion tests ──→ STORY-006: retry enhancement
└── STORY-006: retry enhancement

EPIC-003: Data Source
├── STORY-007: yfinance tests
├── STORY-008: filters tests
└── STORY-009: scanner tests

EPIC-004: Observability
├── STORY-010: health enhancement
├── STORY-011: runbook
└── STORY-012: monitoring spec
```

---

# 📅 Sprint Plan

## Week 1 (Current)
| Story | Estimate | Goal |
|-------|----------|------|
| STORY-001 | M | analytics 23%→80% |
| STORY-002 | S | cache 19%→85% |
| STORY-003 | M | signal_tracker 14%→75% |
| STORY-004 | S | Integration smoke test |

**Week 1 Target:** Coverage 50% → 60%

## Week 2
| Story | Estimate | Goal |
|-------|----------|------|
| STORY-005 | L | notion_client tests |
| STORY-006 | M | Retry enhancement |

**Week 2 Target:** Coverage 60% → 65%, ADR-004

## Week 3
| Story | Estimate | Goal |
|-------|----------|------|
| STORY-007 | M | yfinance tests |
| STORY-008 | S | filters tests |
| STORY-009 | M | scanner tests |

**Week 3 Target:** Coverage 65% → 75%

## Week 4
| Story | Estimate | Goal |
|-------|----------|------|
| STORY-010 | S | Health enhancement |
| STORY-011 | M | Runbook |
| STORY-012 | S | Monitoring spec |

**Week 4 Target:** Operational docs complete

---

# 🎯 Success Metrics

| Metric | Current | Week 1 | Week 2 | Week 3 | Week 4 |
|--------|---------|--------|--------|--------|--------|
| Test Coverage | 50% | 60% | 65% | 75% | 75% |
| Test Count | 163 | 200+ | 230+ | 270+ | 280+ |
| ADRs | 3 | 3 | 4 | 4 | 4 |
| Docs Updated | - | ✓ | ✓ | ✓ | ✓ |
| Production Issues | 0 | 0 | 0 | 0 | 0 |

---

# ⚠️ Risk Register

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Test breaks production | HIGH | LOW | All tests use mocks |
| Coverage target missed | MEDIUM | MEDIUM | Prioritize critical paths |
| Notion API changes | MEDIUM | LOW | Version pin, monitor changelog |
| Sprint overrun | LOW | MEDIUM | Cut scope, not quality |

---

# ✅ Definition of Done (Per Story)

- [ ] Code changes complete
- [ ] All tests pass locally
- [ ] Coverage target met
- [ ] CI pipeline green
- [ ] Ruff lint clean
- [ ] PR ≤ 500 lines
- [ ] README/docs updated if behavior changes
- [ ] Deployed to production (if applicable)
- [ ] No new errors in Sentry (24h)
