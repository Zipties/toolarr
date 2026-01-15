# Toolarr vs Skills - Improvement Tracker

Living document tracking improvements discovered during benchmarking.

---

## Toolarr Improvements

### CRITICAL - Missing Functionality
- [ ] **Add GET /series endpoint** - Can't list library without this! Only has POST (add) and GET by ID
- [ ] **Add GET /movie endpoint** - Same issue for Radarr
- [ ] **Add search-in-library** - Endpoint to search existing library, not just external lookup
- [ ] **Add /release endpoints** - MAJOR GAP: No way to browse/select specific releases!
  - Skills can: `GET /api/v3/release?movieId=X` → browse releases → `POST /release` with specific GUID
  - Toolarr only has: `/movie/{id}/search` which triggers auto-search (Radarr picks for you)
  - This removes user choice entirely - can't pick by size, seeders, or release group
- [ ] **Add episode release browsing** - Same gap for Sonarr episodes

### Architecture
- [ ] **Convert to proper MCP server** - Currently HTTP+JSON-RPC hybrid, should be pure stdio MCP
- [ ] **Remove HTTP gateway overhead** - Direct MCP = faster
- [ ] **Lazy tool registration** - Only load tools when needed

### Efficiency
- [ ] **Batch operations** - Add bulk endpoints (add multiple series at once)
- [ ] **Pagination defaults** - Queue returns 10 by default, should match Sonarr's 50
- [ ] **Response filtering** - Return minimal fields by default, full with `?verbose=true`
- [ ] **Connection pooling** - Reuse HTTP connections to Sonarr/Radarr

### Guardrails
- [ ] **Better error messages** - Include "did you mean X?" suggestions
- [ ] **Rate limiting** - Prevent AI from hammering APIs
- [ ] **Audit logging** - Track what AI does for debugging
- [ ] **Dry-run mode** - Preview changes before executing

### Developer Experience
- [ ] **Auto-generate from OpenAPI** - Keep MCP tools in sync with API changes
- [ ] **Test suite** - Automated tests for all tools
- [ ] **Docker healthcheck** - Proper health endpoint

---

## Skills Improvements

### Patterns
- [ ] **More error handling patterns** - Show how to check HTTP status codes
- [ ] **Retry patterns** - When to retry vs fail
- [ ] **State management** - Better /tmp file conventions
- [ ] **Parallel operations** - When safe to run concurrent curls

### Safety
- [ ] **Read-only mode examples** - Patterns that can't modify data
- [ ] **Confirmation patterns** - "Show what would happen" before executing
- [ ] **Rollback patterns** - How to undo common operations

### Efficiency
- [ ] **Cached lookups** - Store frequently-used IDs (quality profiles, root folders)
- [ ] **Combined operations** - More "do X and Y in one command" patterns
- [ ] **Streaming responses** - Handle large result sets without loading all into memory

### Guardrails
- [ ] **Input validation examples** - Check params before curl
- [ ] **URL encoding helper** - Standard function for encoding search terms
- [ ] **JSON validation** - Check response is valid before jq processing

---

## Test Observations

### Test 1: Severance Lookup (Haiku Agents)
- **Task**: Search for "Severance", check library, get quality profiles
- **Toolarr behavior**:
  - ✅ Lookup worked
  - ❌ `/series` returned 405 Method Not Allowed (no GET endpoint to list library!)
  - ✅ Quality profiles worked
  - Agent noted the limitation but completed task
- **Skills behavior**:
  - ✅ All three operations worked perfectly
  - Direct Sonarr API has GET `/api/v3/series` to list library
- **Insights**:
  - **CRITICAL BUG**: Toolarr is missing a "list all series" endpoint!
  - Toolarr only has POST `/series` (add) and GET `/series/{id}` (get one)
  - Skills has full API access, Toolarr is incomplete

### Key Gaps Discovered

| Operation | Skills | Toolarr | Gap |
|-----------|--------|---------|-----|
| List all series | ✅ GET /series | ❌ Missing | **CRITICAL** |
| List all movies | ✅ GET /movie | ❌ Missing | **CRITICAL** |
| Search library | ✅ jq filter | ❌ Can't list | Blocked by above |
| Check if exists | ✅ Works | ❌ Can't do | Blocked by above |
| Browse releases | ✅ GET /release | ❌ Missing | **CRITICAL** |
| Pick specific release | ✅ POST /release | ❌ Missing | **CRITICAL** |
| Manual download | ✅ Works | ❌ Only auto-search | User has no choice |

### Test 2: Movie Release Browsing (Haiku Agents)
- **Task**: Find Dune (2021), get releases, find best 1080p
- **Toolarr behavior**:
  - ✅ Lookup worked (found TMDB ID)
  - ❌ No releases endpoint exists!
  - 🔄 Agent went in circles for 20+ iterations trying endpoints that don't exist
  - Agent tried: `/releases`, `/movie/{id}/releases`, `/release`, many variations
  - Never found one because it literally doesn't exist in Toolarr
- **Skills behavior**:
  - ✅ All operations worked
  - Found movie, checked library, got releases, filtered 1080p, sorted by seeders
  - Even added movie to library when it wasn't there
- **Insights**:
  - **Toolarr is fundamentally incomplete for release selection workflows**
  - The "guardrails" become a cage - AI can't do what user needs
  - Skills wins here because full API access = full capability

---

## Metrics Comparison

| Metric | Toolarr | Skills | Notes |
|--------|---------|--------|-------|
| Avg response time | ~250ms | ~100ms | Skills ~2.5x faster |
| Success rate | 2/3 | 3/3 | Toolarr missing list endpoint |
| Recovery from errors | Good | Depends on AI | Toolarr returns clear HTTP errors |
| Token usage | ~250/call | ~150/call | Tool schemas add overhead |

---

## Final Verdict

### Toolarr: Not Production Ready

**Pros:**
- Typed schemas prevent malformed requests
- Clear HTTP error codes
- Instance abstraction prevents hallucination
- Good for simple lookup/add workflows

**Cons:**
- Missing critical endpoints (list library, browse releases, manual download)
- HTTP gateway adds latency (~2.5x slower)
- Tool schemas increase token usage
- "Guardrails" become a cage when features are missing

**Recommendation:** Needs significant development before viable. Add missing endpoints, then convert to pure MCP.

### Skills: Production Ready (for capable models)

**Pros:**
- Full API access = full capability
- Faster (direct API calls)
- Lower token overhead
- Can do everything Sonarr/Radarr can do

**Cons:**
- Requires AI that follows instructions well
- No schema validation (AI must construct valid requests)
- Bash access means potential for mistakes
- Needs more patterns for error handling

**Recommendation:** Use for Sonnet/Opus. Add more patterns for edge cases. Consider "safe mode" wrapper for Haiku.

### Hybrid Approach?

Best of both worlds could be:
1. **Skills for capable models** - Full power, full speed
2. **Toolarr (improved) for dumb models** - Safe but complete
3. **Skills with validation layer** - Check params before curl execution

---

## Next Steps

1. [ ] Add missing Toolarr endpoints (list, releases, manual grab)
2. [ ] Convert Toolarr to pure MCP (remove HTTP overhead)
3. [ ] Add Skills validation helpers (URL encoding, param checking)
4. [ ] Create "safe mode" Skills wrapper for Haiku
5. [ ] Benchmark again after improvements
