# Module: matching

- **Owner**: M2
- **Responsibilities**: Heuristic match scoring, recommendation feed, cold-start fairness, and giver profile discovery.
- **Migrations Branch**: `matching` (stored in `migrations/`)

---

## 1. Score v1: Honest Heuristic Match Formula

Matching Score v1 is explicitly designed and labelled as an **explainable heuristic**, not a black-box model. It computes a transparent, normalized match score \([0.0, 1.0]\) from 6 distinct components:

| Component | Weight | Calculation Method |
|---|:---:|---|
| **Expertise Fit** | 35% | 70% Cosine similarity of student profile embedding vs giver embedding + 30% Jaccard keyword overlap of technical skills and domains. |
| **Intent Fit** | 25% | 60% Cosine similarity of student intent embedding vs giver offers embedding + 40% exact help type match (e.g. `mock_interview`, `resume_review`). |
| **Affinity** | 15% | Same institution (+0.40), same department (+0.30), batch proximity 1–4 years senior (+0.20), shared college society (+0.10). |
| **Availability** | 10% | Online now (+0.70) vs offline (+0.20), plus open weekly booking window capacity (+0.30). |
| **Rating** | 10% | Smoothed rating average \((smoothed - 1.0) / 4.0\) (60%) + Rating band weight (Top Rated 1.0, Trusted 0.85, Rising 0.70) (40%). |
| **Response Odds** | 5% | Historical acceptance rate (60%) + median response time speed score (40%). |

### Cold-Start Fairness & Exposure Caps
- **Cold-Start Boost**: New givers with fewer than 5 rated sessions receive a `+0.08` exposure boost to ensure they receive early session opportunities and can earn ratings.
- **Daily Exposure Cap**: Givers who reach 25 impressions per day (`MAX_DAILY_EXPOSURE = 25`) are temporarily capped to prevent flooding and protect giver capacity.

---

## 2. Hard Gates (Never Weights)

Candidates must strictly satisfy all hard gates before any scoring occurs. If any gate fails, the candidate is excluded:
1. **Giver Verification**: Giver must be verified and not restricted (`TrustPort.get_level(giver_id)` in `['verified', 'established']`).
2. **Safety Blocks**: Communication must not be blocked between student and giver (`TrustPort.is_blocked`).
3. **Weekly Capacity**: Giver must have remaining weekly session capacity (`PresencePort.status` capacity > 0).
4. **Self-Exclusion**: Giver cannot be the requesting student.
5. **Student Verification**: Student must have completed college verification (`TrustPort.get_level(student_id)`).

---

## 3. Explainability (`why_lines`)

Every recommended candidate includes deterministic, human-readable `why_lines` explaining why the mentor was selected (e.g., *"Shares your Python and FastAPI skills"*, *"Offers mock interview, which matches your goal"*, *"Same college, 2 years ahead"*, *"Online now for instant connection"*). Raw embeddings and algorithmic weights are never shown to students.

`MatchingPort.explain(student_id, giver_id)` exposes the identical explainability lines for the `sessions` module.

---

## 4. Performance & Caching

1. **pgvector HNSW Search**: Retrieves top 200 candidate profiles by vector cosine distance.
2. **Python Re-Ranking**: Applies hard gates, score components, cold-start boost, and daily exposure caps.
3. **Redis Caching**: Caches ranked candidates per student for 60 seconds (`wp:rec:{student_id}:{scope}:{filter_hash}`).
4. **Reactive Cache Invalidation**: Listens to outbox events:
   - `profile.updated`: Clears student's cached recommendations.
   - `giver.profile_updated`: Clears affected giver caches.
   - `band.changed`: Clears affected giver caches.

---

## 5. Contract Endpoints
- `GET /recommendations`: Get ranked mentor recommendations for student (`own_college`, `cross_college`, `experts`) with cursor pagination.
- `GET /givers/{id}`: View public giver mentorship profile card (contact details strictly masked).
- `PUT /me/giver-profile`: Update own giver mentorship profile, topics, and embeddings.
- `GET /me/giver-profile`: Retrieve own giver mentorship profile.
