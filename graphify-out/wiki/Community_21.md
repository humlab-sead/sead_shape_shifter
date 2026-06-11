# Community 21

> 63 nodes · cohesion 0.09

## Key Concepts

- **TableSchema** (32 connections) — `backend/app/models/data_source.py`
- **TableMetadata** (25 connections) — `backend/app/models/data_source.py`
- **SuggestionService** (24 connections) — `backend/app/services/suggestion_service.py`
- **EntitySuggestions** (19 connections) — `backend/app/models/suggestion.py`
- **SuggestionService** (18 connections) — `backend/app/api/v1/endpoints/suggestions.py`
- **suggestion.py** (16 connections) — `backend/app/models/suggestion.py`
- **ForeignKeySuggestion** (16 connections) — `backend/app/models/suggestion.py`
- **DependencySuggestion** (16 connections) — `backend/app/models/suggestion.py`
- **Any** (12 connections) — `backend/app/services/suggestion_service.py`
- **TableSchema** (12 connections) — `backend/app/services/suggestion_service.py`
- **ColumnMatchStrategy** (11 connections) — `backend/app/services/suggestion_service.py`
- **ExactColumnMatch** (11 connections) — `backend/app/services/suggestion_service.py`
- **ForeignKeyPatternColumnMatch** (11 connections) — `backend/app/services/suggestion_service.py`
- **RemoteEntityPatternColumnMatch** (11 connections) — `backend/app/services/suggestion_service.py`
- **._find_column_matches()** (9 connections) — `backend/app/services/suggestion_service.py`
- **SuggestionsRequest** (8 connections) — `backend/app/models/suggestion.py`
- **SchemaIntrospectionService** (8 connections) — `backend/app/services/suggestion_service.py`
- **.suggest_foreign_keys()** (8 connections) — `backend/app/services/suggestion_service.py`
- **ForeignKeySuggestion** (8 connections) — `backend/app/services/suggestion_service.py`
- **._calculate_fk_confidence()** (8 connections) — `backend/app/services/suggestion_service.py`
- **SchemaIntrospectionService** (7 connections) — `backend/app/api/v1/endpoints/suggestions.py`
- **analyze_entities()** (7 connections) — `backend/app/api/v1/endpoints/suggestions.py`
- **.suggest_for_entity()** (7 connections) — `backend/app/services/suggestion_service.py`
- **EntitySuggestions** (7 connections) — `backend/app/services/suggestion_service.py`
- **DependencySuggestion** (7 connections) — `backend/app/services/suggestion_service.py`
- *... and 38 more nodes in this community*

## Relationships

- [[Community 40]] (30 shared connections)
- [[Community 2]] (13 shared connections)
- [[Community 11]] (5 shared connections)
- [[Community 1]] (3 shared connections)
- [[Community 83]] (2 shared connections)
- [[Community 3]] (2 shared connections)
- [[Community 6]] (2 shared connections)
- [[Community 85]] (2 shared connections)
- [[Community 39]] (1 shared connections)
- [[Community 52]] (1 shared connections)

## Source Files

- `backend/app/api/v1/endpoints/suggestions.py`
- `backend/app/models/data_source.py`
- `backend/app/models/suggestion.py`
- `backend/app/services/suggestion_service.py`

## Audit Trail

- EXTRACTED: 231 (57%)
- INFERRED: 172 (43%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*