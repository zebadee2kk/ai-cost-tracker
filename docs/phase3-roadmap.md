# AI Cost Tracker: Phase 3 Master Roadmap

**Version**: 1.0  
**Created**: February 25, 2026  
**Status**: Ready for Implementation  
**Timeline**: 6-8 weeks total

---

## Overview

Phase 3 transforms the AI Cost Tracker from a monitoring tool into a **proactive cost management platform** with exports, visual indicators, CI/CD, notifications, and predictive analytics.

### Phase 3 Goals
1. **Export Capability** - Download data for external analysis
2. **Source Transparency** - Distinguish API vs manual data visually
3. **Automation** - CI/CD pipeline for quality assurance
4. **Proactive Alerts** - Email/webhook notifications for budget breaches
5. **Predictive Insights** - Forecasting and anomaly detection

---

## Feature Matrix

| Feature | Priority | Effort | Status | Dependencies | Document |
|---------|----------|--------|--------|--------------|----------|
| **CSV/JSON Export** | P0 | 1 week | ⏳ Ready | None | [phase3-export-spec.md](./phase3-export-spec.md) |
| **Visual Source Badges** | P0 | 1 week | ⏳ Ready | None | [phase3-visual-indicators-spec.md](./phase3-visual-indicators-spec.md) |
| **CI/CD Pipeline** | P1 | 1 week | ⏳ Ready | GitHub Actions | [phase3-ci-guide.md](./phase3-ci-guide.md) |
| **Notifications** | P1 | 2-3 weeks | ⏳ Ready | SendGrid account | [phase3-notifications-spec.md](./phase3-notifications-spec.md) |
| **Analytics & Forecasting** | P2 | 2-3 weeks | ⏳ Ready | scikit-learn | [phase3-analytics-spec.md](./phase3-analytics-spec.md) |

---

## Timeline

### Option A: Sequential Implementation (8 weeks)

```
Week 1-2:   CSV/JSON Export System
Week 3:     Visual Source Indicators
Week 4:     CI/CD Pipeline Setup
Week 5-6:   Notification System
Week 7-8:   Analytics & Forecasting
```

**Pros**: Lower cognitive load, one feature at a time  
**Cons**: Slower time-to-value

### Option B: Parallel Implementation (6 weeks) ✅ **RECOMMENDED**

```
Week 1-2:   [Track 1] CSV/JSON Export + Visual Indicators
            [Track 2] CI/CD Pipeline Setup

Week 3-4:   [Track 1] Notification System (Email + Slack)
            [Track 2] Analytics (Forecasting)

Week 5-6:   [Track 1] Notification System (Discord + Teams)
            [Track 2] Analytics (Anomaly Detection)
            [Track 3] Integration Testing & Polish
```

**Pros**: Faster delivery, features complement each other  
**Cons**: Requires 2 developers or AI agents working in parallel

---

## Detailed Schedule (Parallel Track)

### Sprint 1: Export + Visual + CI (Weeks 1-2)

#### Track 1: Frontend Features (Days 1-10)
**Owner**: Claude Code / Frontend Developer

**Week 1 (Days 1-5)**:
- Day 1-2: Implement CSV/JSON export API endpoints
- Day 3: Create ExportButton component with format selector
- Day 4-5: Add streaming export for large datasets
- **Deliverable**: Users can export usage data in CSV/JSON

**Week 2 (Days 6-10)**:
- Day 6-7: Create SourceBadge component (API vs Manual)
- Day 8: Integrate Chart.js custom point styles
- Day 9: Add SourceFilter component
- Day 10: Testing + documentation
- **Deliverable**: Visual distinction between data sources

#### Track 2: CI/CD Setup (Days 1-10)
**Owner**: Codex / DevOps Engineer

**Week 1 (Days 1-5)**:
- Day 1-2: Create `.github/workflows/ci.yml`
- Day 3: Configure backend tests with PostgreSQL service
- Day 4: Configure frontend tests with coverage
- Day 5: Add security scanning (Bandit, npm audit, Trivy)
- **Deliverable**: CI pipeline runs on every PR

**Week 2 (Days 6-10)**:
- Day 6-7: Set up Codecov.io integration
- Day 8: Configure Docker build (main branch only)
- Day 9: Add branch protection rules
- Day 10: Documentation + troubleshooting guide
- **Deliverable**: Full CI/CD pipeline operational

---

### Sprint 2: Notifications + Analytics Core (Weeks 3-4)

#### Track 1: Notification System (Days 11-20)
**Owner**: Claude Code / Backend Developer

**Week 3 (Days 11-15)**:
- Day 11-12: Database migrations (notification_preferences, queue)
- Day 13: Implement EmailSender class (SendGrid)
- Day 14: Create email templates (budget, anomaly, system)
- Day 15: Implement SlackSender class
- **Deliverable**: Email + Slack notifications working

**Week 4 (Days 16-20)**:
- Day 16: Implement alert generation job (APScheduler)
- Day 17: Implement notification dispatcher job
- Day 18: Add rate limiting logic
- Day 19: Create NotificationSettingsPage (frontend)
- Day 20: Testing + documentation
- **Deliverable**: Full notification system with 2 channels

#### Track 2: Analytics & Forecasting (Days 11-20)
**Owner**: Claude Code / Data Engineer

**Week 3 (Days 11-15)**:
- Day 11-12: Implement CostForecaster class (Linear Regression)
- Day 13: Add `/api/analytics/forecast` endpoint
- Day 14: Test forecasting accuracy (MAPE <15%)
- Day 15: Create EnhancedAnalyticsPage (frontend)
- **Deliverable**: 30/60/90-day cost forecasting

**Week 4 (Days 16-20)**:
- Day 16-17: Implement AnomalyDetector class (Z-score)
- Day 18: Add `/api/analytics/anomalies` endpoint
- Day 19: Integrate anomaly markers into charts
- Day 20: Testing + documentation
- **Deliverable**: Anomaly detection with visual indicators

---

### Sprint 3: Extend + Polish (Weeks 5-6)

#### Track 1: Additional Notification Channels (Days 21-25)
**Owner**: Claude Code

- Day 21-22: Implement DiscordSender class
- Day 23-24: Implement Microsoft Teams sender (optional)
- Day 25: Add test notification endpoints
- **Deliverable**: 3-4 notification channels supported

#### Track 2: Advanced Analytics (Days 21-25)
**Owner**: Claude Code

- Day 21: Add budget burn rate tracking
- Day 22: Add model-level cost breakdown (GPT-4 vs Claude)
- Day 23: Add trend analysis (MoM, QoQ comparisons)
- Day 24-25: Performance optimization (<2s page load)
- **Deliverable**: Complete analytics dashboard

#### Track 3: Integration Testing (Days 26-30)
**Owner**: Codex / QA Engineer

- Day 26-27: End-to-end testing (export + notify + forecast)
- Day 28: Cross-browser testing (Chrome, Firefox, Safari)
- Day 29: Performance testing (load times, API response)
- Day 30: Security audit + documentation review
- **Deliverable**: Production-ready Phase 3

---

## Success Metrics

### Export System
- ✅ **Target**: 40% of users export data monthly
- **Measurement**: Track export button clicks

### Visual Indicators
- ✅ **Target**: 95% users correctly identify data sources
- **Measurement**: Usability survey (5 questions)

### CI/CD
- ✅ **Target**: >80% test coverage (backend), >70% (frontend)
- **Measurement**: Codecov dashboard

### Notifications
- ✅ **Target**: >95% delivery success rate
- **Measurement**: `sent / queued * 100`

### Analytics
- ✅ **Target**: <15% MAPE for 30-day forecasts
- **Measurement**: Compare predictions to actual costs

---

## Risk Management

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Insufficient historical data** | Medium | High | Require 14+ days before enabling forecasting |
| **Email deliverability issues** | Low | Medium | Use SendGrid with high reputation score |
| **False positive anomalies** | Medium | Low | Tune Z-score threshold based on user feedback |
| **CI/CD exceeds free tier** | Low | Low | Optimize job runtime, use caching |
| **Export performance issues** | Medium | Medium | Implement streaming for >10k records |

---

## Dependencies

### External Services (Free Tier Sufficient)
- **SendGrid**: Email notifications (100/day free)
- **Codecov**: Coverage reporting (unlimited for open source)
- **Docker Hub**: Container registry (1 private repo free)

### Python Libraries
```
scikit-learn==1.4.0    # Forecasting
sendgrid==6.11.0       # Email
APScheduler==3.10.4    # Background jobs
```

### npm Packages
```
chart.js==4.4.1        # Charts
react-chartjs-2==5.2.0 # React wrapper
```

---

## Handover to Implementation

### For Claude Code (Development)

**Starting Points**:
1. **Week 1-2**: Implement export system ([phase3-export-spec.md](./phase3-export-spec.md))
2. **Week 1-2**: Add visual indicators ([phase3-visual-indicators-spec.md](./phase3-visual-indicators-spec.md))
3. **Week 3-4**: Build notification system ([phase3-notifications-spec.md](./phase3-notifications-spec.md))
4. **Week 3-4**: Create analytics features ([phase3-analytics-spec.md](./phase3-analytics-spec.md))

**Instructions**:
- Each spec document contains complete code examples
- Follow the implementation checklists in each document
- Write tests for every feature (target >80% coverage)
- Commit frequently with descriptive messages
- Open PR when feature is complete + tested

### For Codex (Review & Validation)

**Review Checklist**:
- [ ] Code follows style guidelines (Black for Python, ESLint for JS)
- [ ] All functions have docstrings/comments
- [ ] Tests written and passing (>80% coverage)
- [ ] No security vulnerabilities (Bandit, npm audit clean)
- [ ] API endpoints documented
- [ ] Error handling implemented
- [ ] Performance acceptable (<2s page load, <500ms API)

**Testing Focus**:
- Export: Test with 1k, 10k, 100k records
- Notifications: Test delivery + rate limiting
- Forecasting: Validate MAPE <15%
- Anomaly detection: Test false positive rate

### For Perplexity (Coordination)

**Status Tracking**:
- Weekly progress updates from Claude Code
- Weekly code review reports from Codex
- Escalate blockers immediately
- Coordinate sprint planning

**Decision Points**:
- Week 2: Export + visual indicators complete? Proceed to notifications
- Week 4: Core features complete? Proceed to polish sprint
- Week 6: Phase 3 complete? Plan Phase 4 kickoff

---

## Phase 3 Completion Checklist

### Features
- [ ] CSV/JSON export working (tested with 10k+ records)
- [ ] Visual source badges on all data points
- [ ] CI/CD pipeline passing on all PRs
- [ ] Email notifications delivered successfully
- [ ] Slack notifications working
- [ ] 30/60/90-day forecasting accurate (<15% MAPE)
- [ ] Anomaly detection with <10% false positives

### Quality
- [ ] Backend test coverage >80%
- [ ] Frontend test coverage >70%
- [ ] Zero high-severity security vulnerabilities
- [ ] All API endpoints documented
- [ ] User documentation updated

### Performance
- [ ] Export <30s for 100k records
- [ ] Analytics page loads in <2s
- [ ] Notification delivery <5 min from threshold breach

### Deployment
- [ ] Docker images built and pushed
- [ ] Environment variables documented
- [ ] Migration scripts tested
- [ ] Rollback plan documented

---

## Next Steps After Phase 3

### Phase 4 Preview (Future)

**Cost Optimization Features**:
- Model comparison tool (GPT-4 vs Claude 3.5 vs Haiku)
- Cost-per-query analysis
- Batch processing recommendations
- Caching effectiveness metrics

**Team Features**:
- Multi-user support (team accounts)
- Role-based access control (admin, viewer, editor)
- Shared dashboards
- Team budgets with sub-allocations

**Advanced Analytics**:
- Usage heatmaps (day-of-week, hour-of-day)
- Cohort analysis (new vs returning queries)
- A/B test cost tracking
- Custom report builder

**Integrations**:
- LangSmith integration
- OpenTelemetry tracing
- Grafana dashboard export
- Slack bot for quick queries

---

## Resources

### Documentation
- [Phase 3 Export Spec](./phase3-export-spec.md)
- [Phase 3 Visual Indicators Spec](./phase3-visual-indicators-spec.md)
- [Phase 3 CI/CD Guide](./phase3-ci-guide.md)
- [Phase 3 Notifications Spec](./phase3-notifications-spec.md)
- [Phase 3 Analytics Spec](./phase3-analytics-spec.md)

### External References
- [SendGrid API Docs](https://docs.sendgrid.com/api-reference)
- [Chart.js Point Styles](https://www.chartjs.org/docs/latest/configuration/elements.html#point-styles)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [scikit-learn Linear Regression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html)

### Communication
- **Slack Channel**: #ai-cost-tracker-dev
- **GitHub Issues**: Tag with `phase-3` label
- **Weekly Sync**: Mondays 10am GMT

---

**Roadmap Version**: 1.0  
**Last Updated**: February 25, 2026  
**Next Review**: Weekly (every Monday)

**Status**: ✅ Ready for Implementation  
**Go/No-Go Decision**: ✅ **GO** - All specifications complete, dependencies identified, resources allocated
