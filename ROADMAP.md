# AI Cost Tracker - Project Roadmap

**Last Updated**: February 25, 2026  
**Current Phase**: Phase 2 (Multi-Service Integration)

---

## ✅ Phase 1: MVP Foundation (COMPLETED)

**Status**: ✅ **Complete** - Delivered February 2026

### Delivered Features

#### Backend
- [x] Flask application with app factory pattern
- [x] JWT authentication system (register, login, logout)
- [x] SQLAlchemy models: users, services, accounts, usage_records, alerts, cost_projections
- [x] AES-256 Fernet encryption for API keys at rest
- [x] RESTful API endpoints:
  - [x] Account management (CRUD + test connection)
  - [x] Service management (list, get, update pricing)
  - [x] Usage tracking (current month, history, by-service aggregation, forecasting)
  - [x] Alert system (CRUD, acknowledge)
- [x] OpenAI API integration with usage sync
- [x] APScheduler background job for periodic sync
- [x] Cost calculation and alert generation utilities
- [x] Database migrations (Alembic)
- [x] Docker containerization

#### Frontend
- [x] React application with routing
- [x] Authentication context and protected routes
- [x] Login and registration screens
- [x] Dashboard with:
  - [x] Overview cards (current month spend, total usage)
  - [x] Usage charts and visualizations
  - [x] Account manager
  - [x] Alert panel
- [x] Analytics page with pie charts and forecasting
- [x] Settings page
- [x] Axios API client with JWT token management

#### Testing
- [x] Encryption utility tests
- [x] Auth integration tests
- [x] Account integration tests
- [x] OpenAI service parser tests

#### Documentation
- [x] Setup quickstart guide
- [x] API integration guide
- [x] Project planning documentation
- [x] Handover documentation (Codex → Perplexity)

### Known Limitations
- Only OpenAI service has live API sync
- Scheduler lacks idempotency (can create duplicates)
- Limited test coverage for usage/alert routes
- Connection test only works for OpenAI

---

## 🔵 Phase 2: Multi-Service Integration (IN PROGRESS)

**Status**: 🔵 **Ready to Start** - Research Complete, Handover Prepared  
**Target**: March 2026  
**Assigned To**: Claude Code

### Objectives
1. Expand from OpenAI-only to multi-provider support
2. Ensure data integrity through idempotent ingestion
3. Implement manual entry system for providers without APIs
4. Achieve robust test coverage

### Sprint 2.1: Foundation & Anthropic (Weeks 1-2)

#### Data Integrity
- [ ] Add unique constraint for idempotent usage records
- [ ] Implement ON CONFLICT upsert in scheduler
- [ ] Fix scheduler duplicate runs in debug mode
- [ ] Add `source` and `updated_at` fields to usage_records

#### Anthropic Claude Integration
- [ ] Implement `AnthropicService` class
- [ ] Support Admin API key authentication
- [ ] Parse usage and cost endpoints
- [ ] Normalize response to standard format
- [ ] Add unit tests with mocked responses
- [ ] Integration test with real API
- [ ] Update service dispatch mapping
- [ ] Extend connection test endpoint

#### Testing & CI
- [ ] Unit tests for Anthropic service
- [ ] Integration tests for idempotent upsert
- [ ] Scheduler duplicate prevention tests
- [ ] GitHub Actions CI pipeline

**Definition of Done**:
- ✅ Multi-provider sync runs without duplicates
- ✅ Anthropic accounts can be added and synced
- ✅ Backend tests pass in CI
- ✅ Test coverage >80%

### Sprint 2.2: Manual Entry System (Weeks 2-3)

**For**: Groq, Perplexity, GitHub Copilot, local LLMs

#### Backend
- [ ] Manual entry endpoint (`POST /api/usage/manual`)
- [ ] Edit manual entry endpoint (`PUT /api/usage/manual/:id`)
- [ ] Delete manual entry endpoint (`DELETE /api/usage/manual/:id`)
- [ ] Validation for manual entries
- [ ] Source field tracking (api vs. manual)

#### Frontend
- [ ] "Add Manual Entry" button in account manager
- [ ] Manual entry modal with form:
  - [ ] Date picker
  - [ ] Token count input
  - [ ] Cost input
  - [ ] Notes field
- [ ] Visual indicators for manual vs. API entries
- [ ] Edit/delete manual entry actions
- [ ] Help text with provider-specific instructions
- [ ] Link to provider dashboards

#### User Experience
- [ ] Groq: Dashboard → Usage instructions
- [ ] Perplexity: Settings → Usage Metrics → Invoices guide
- [ ] Clear labeling: "Manual Entry Required - No API Available"

**Definition of Done**:
- ✅ Users can add manual entries for any service
- ✅ Manual entries clearly distinguished from API data
- ✅ Edit/delete functionality working
- ✅ Help documentation accessible

### Sprint 2.3: Polish & Documentation (Week 4)

#### Code Cleanup
- [ ] Remove unused imports from scheduler
- [ ] Clean up unused variables
- [ ] Code review and refactoring
- [ ] Error handling improvements

#### Documentation
- [ ] Update README with:
  - [ ] Phase 1 completion status
  - [ ] Anthropic setup instructions
  - [ ] Manual entry workflow guide
  - [ ] Troubleshooting section
- [ ] API documentation updates
- [ ] Deployment guide improvements

#### Testing
- [ ] End-to-end test: seed usage → verify dashboard
- [ ] Load testing for scheduler
- [ ] Edge case testing (invalid dates, negative costs, etc.)

**Definition of Done**:
- ✅ Documentation complete and accurate
- ✅ All tests passing
- ✅ Code clean and maintainable
- ✅ Ready for production deployment

### Phase 2 Deliverables

**Supported Services**:
- ✅ OpenAI (existing)
- ✅ Anthropic Claude (new - API integration)
- ✅ Groq (new - manual entry)
- ✅ Perplexity (new - manual entry)

**Key Features**:
- Idempotent data ingestion (no duplicates)
- Multi-provider cost tracking
- Hybrid API + manual entry support
- Improved test coverage
- Production-ready scheduler

### Research Complete
See [docs/research-api-capabilities-2026.md](docs/research-api-capabilities-2026.md) for:
- Detailed API capabilities for each provider
- Idempotent ingestion patterns
- Implementation code examples
- Best practices and recommendations

---

## 🟡 Phase 3: Product Enhancement (PLANNED)

**Target**: April-May 2026  
**Status**: ⏳ Planning

### Proposed Features

#### Data Export
- [ ] CSV export endpoint
- [ ] JSON export endpoint
- [ ] Date range filtering
- [ ] Per-service export
- [ ] Frontend export buttons

#### Enhanced Analytics
- [ ] Cost trends over time
- [ ] Usage anomaly detection
- [ ] Budget forecasting improvements
- [ ] Cost breakdown by model/feature
- [ ] Comparative analytics (month-over-month)

#### Alert Enhancements
- [ ] Email notifications
- [ ] Webhook support
- [ ] Slack integration
- [ ] Custom alert thresholds
- [ ] Alert history and analytics

#### Additional Integrations
- [ ] Gemini/Google AI API (if usage API available)
- [ ] Mistral AI (if usage API available)
- [ ] Cohere (if usage API available)
- [ ] Custom API integration framework

#### User Experience
- [ ] Dark mode
- [ ] Mobile responsive design
- [ ] Onboarding tutorial
- [ ] In-app help system
- [ ] Keyboard shortcuts

#### Administration
- [ ] Multi-user support (teams)
- [ ] Role-based access control
- [ ] Audit logging
- [ ] Usage quotas and limits

---

## 🟠 Phase 4: Enterprise & Scale (FUTURE)

**Target**: Q3 2026  
**Status**: 🔮 Concept

### Potential Features

#### Enterprise Features
- [ ] SSO integration (SAML, OAuth)
- [ ] Multi-tenancy
- [ ] White-label customization
- [ ] SLA monitoring
- [ ] Dedicated support

#### Scalability
- [ ] Redis caching layer
- [ ] Database read replicas
- [ ] Horizontal scaling support
- [ ] CDN integration
- [ ] Performance monitoring

#### Advanced Analytics
- [ ] Machine learning cost predictions
- [ ] Optimization recommendations
- [ ] Benchmark comparisons
- [ ] ROI calculations

#### Monetization (Optional)
- [ ] SaaS offering
- [ ] Tiered pricing plans
- [ ] API access for third parties
- [ ] Consulting services

---

## 📊 Success Metrics

### Phase 1 (Achieved)
- ✅ Functional MVP with OpenAI integration
- ✅ User authentication and account management
- ✅ Dashboard with usage visualization
- ✅ Docker deployment ready

### Phase 2 (Targets)
- ✅ Support for 4+ AI services
- ✅ Zero duplicate records in usage sync
- ✅ >80% test coverage
- ✅ <5 minute manual entry workflow

### Phase 3 (Targets)
- Export feature adoption >60% of users
- Alert delivery success rate >95%
- User satisfaction score >4.5/5

---

## 📝 Notes

### API Availability Watch List

Monitoring these providers for usage API announcements:
- **Groq**: Community requested (Aug 2024), no timeline
- **Perplexity**: Feature requested (Apr 2025), no response
- **Gemini**: Investigating availability
- **Mistral**: Investigating availability

When APIs become available, migrate from manual to automated sync.

### Technical Debt

Items to address:
1. Expand test coverage for usage routes
2. Expand test coverage for alert routes
3. Frontend connection test for non-OpenAI services
4. Improve error messages and user feedback
5. Add retry logic for API failures

### Community Feedback

After Phase 2 release:
- Gather user feedback on manual entry UX
- Assess demand for additional services
- Prioritize Phase 3 features based on usage

---

## 🔗 Related Documentation

- [Setup Quickstart](docs/setup-quickstart.md) - Getting started guide
- [API Integration Guide](docs/api-integration-guide.md) - API documentation
- [Research: API Capabilities 2026](docs/research-api-capabilities-2026.md) - Provider research
- [Handover to Claude: Phase 2](docs/handover-to-claude-phase2.md) - Implementation guide
- [Handover to Perplexity](docs/handover-to-perplexity.md) - Phase 1 state review

---

**Maintained By**: AI Team (Codex, Perplexity, Claude Code)  
**Last Review**: February 25, 2026  
**Next Review**: After Phase 2 completion
