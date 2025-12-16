# ADR-001: Notion as Primary Database

**Status:** Accepted  
**Date:** 2025-12-16  
**Decision Makers:** yalintumer

## Context

Signal tracking sistemi için persistent storage gerekli:
- Signals (Stage 1 candidates)
- Buy (confirmed signals)
- Watchlist (deprecated)

Alternatifler değerlendirildi:
1. SQLite (local file)
2. PostgreSQL (VM'de)
3. Notion API
4. Google Sheets API
5. Firebase/Supabase

## Decision

**Notion API** seçildi.

## Rationale

### Neden Notion?

| Kriter | Notion | SQLite | PostgreSQL |
|--------|--------|--------|------------|
| Setup complexity | ✅ 0 (API key) | ✅ 0 | ❌ VM'de DB setup |
| Manual edit | ✅ Web UI | ❌ CLI only | ❌ pgAdmin gerekli |
| Mobile view | ✅ Native app | ❌ Yok | ❌ Yok |
| Backup | ✅ Otomatik | ⚠️ Manuel | ⚠️ pg_dump |
| Collaboration | ✅ Paylaşım | ❌ | ❌ |
| Cost | ✅ Free tier | ✅ Free | ⚠️ VM cost |
| API rate limit | ⚠️ 3 req/s | ✅ Unlimited | ✅ Unlimited |

### Key Benefits

1. **Human-readable UI**: Signals'ı browser'dan görebilme
2. **Zero infra**: Database server yönetimi yok
3. **Mobile friendly**: Notion app ile signal takibi
4. **Easy backup**: JSON export, Git'e commit

### Tradeoffs Kabul Edildi

| Tradeoff | Mitigation |
|----------|------------|
| Rate limit (3 req/s) | rate_limiter.py: 30/min cap |
| 401 errors (token expire) | retry.py: exponential backoff |
| Query performansı | Schema caching |
| Offline unavailable | JSON backup daily |

## Consequences

### Positive
- Hızlı MVP development
- Görsel signal monitoring
- Kolay manual override (archive, edit)

### Negative
- Rate limiting dikkat gerektirir
- Complex queries yapılamaz
- Vendor lock-in (Notion API'ye bağımlılık)

### Neutral
- API token yönetimi (env var ile çözüldü)

## Alternatives Rejected

### SQLite
- ❌ Manual edit için CLI gerekli
- ❌ Mobile'da görüntüleme yok
- ✅ Unlimited queries

### PostgreSQL
- ❌ VM'de DB setup karmaşıklığı
- ❌ Backup stratejisi gerekli
- ✅ Full SQL power

### Google Sheets
- ⚠️ API setup daha karmaşık
- ⚠️ OAuth flow gerekli
- ✅ Benzer UI benefits

## References

- [Notion API Docs](https://developers.notion.com/)
- [Rate Limits](https://developers.notion.com/reference/request-limits)
