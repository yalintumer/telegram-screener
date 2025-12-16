# Architecture Decision Records (ADR)

Bu klasör projenin önemli teknik kararlarını dokümante eder.

## ADR Listesi

| # | Başlık | Durum | Tarih |
|---|--------|-------|-------|
| [ADR-001](ADR-001-notion-as-database.md) | Notion as Primary Database | ✅ Accepted | 2025-12-16 |
| [ADR-002](ADR-002-indicator-selection.md) | Three-Stage Filtering with Specific Indicators | ✅ Accepted | 2025-12-16 |
| [ADR-003](ADR-003-yfinance-data-source.md) | yfinance as Primary Data Source | ✅ Accepted | 2025-12-16 |

## ADR Format

Her ADR şu bölümleri içerir:

1. **Status**: Proposed / Accepted / Deprecated / Superseded
2. **Context**: Problem nedir?
3. **Decision**: Ne kararı verildi?
4. **Rationale**: Neden bu karar?
5. **Consequences**: Sonuçları nelerdir?
6. **Alternatives Rejected**: Neden diğerleri reddedildi?

## Yeni ADR Ekleme

```bash
# Template kopyala
cp docs/adr/ADR-001-notion-as-database.md docs/adr/ADR-XXX-title.md

# Düzenle
nano docs/adr/ADR-XXX-title.md

# Index güncelle
nano docs/adr/README.md
```

## Referanslar

- [ADR GitHub](https://adr.github.io/)
- [Michael Nygard's Template](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
