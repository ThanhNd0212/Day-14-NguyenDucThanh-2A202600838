# Day 14 — Reflection
## Evaluation Report & Failure Analysis

---

## 1. Benchmark Results Summary

*(Results từ Exercise 3.2 — BenchmarkRunner chạy trên 20 QA pairs, domain Sports News)*

**Overall pass rate:** **10.0%** (2/20 passed — E01, E02)

**Average scores:**

| Metric | Average | Min | Max | Std Dev |
|--------|---------|-----|-----|---------|
| Faithfulness | 0.412 | 0.125 | 0.750 | ~0.18 |
| Relevance | 0.467 | 0.091 | 0.875 | ~0.21 |
| Completeness | 0.603 | 0.143 | 0.955 | ~0.20 |
| Overall Score | 0.494 | 0.226 | 0.786 | ~0.15 |

**Score interpretation (theo bài giảng):**
- Bao nhiêu metrics ở Good (0.8–1.0)? **0** metrics
- Bao nhiêu metrics ở Needs Work (0.6–0.8)? **1** metric (Completeness: 0.603)
- Bao nhiêu metrics ở Significant Issues (<0.6)? **2** metrics (Faithfulness: 0.412, Relevance: 0.467)

> **Phân tích tổng quát:** Completeness cao nhất (0.603) vì mock agent lấy được nhiều từ chính từ context sports (tên cầu thủ, số liệu). Faithfulness thấp nhất (0.412) vì nhiều hallucination cases — agent tạo sự kiện không có trong context (ví dụ H04 faith=0.133, A01 faith=0.125). Đây cũng là hạn chế của word-overlap với dữ liệu đa ngôn ngữ: câu trả lời tiếng Anh với context tiếng Việt bị đánh giá thấp hơn thực tế.

**Failure type distribution:**

| Failure Type | Count | Percentage |
|--------------|-------|------------|
| off_topic | 8 | 44.4% |
| hallucination | 7 | 38.9% |
| irrelevant | 3 | 16.7% |
| incomplete | 0 | 0.0% |
| refusal | 0 | 0.0% |

---

## 2. Top 3 Worst Failures — 5 Whys Analysis

Theo bài giảng: "Phân loại failure TRƯỚC KHI fix. Đừng fix từng failure riêng lẻ — CLUSTER rồi fix root cause."

### Failure 1

**Question:** *What made Alcaraz's Roland Garros 2025 victory historically significant beyond just winning the title?*

**Agent Answer:** *"Alcaraz won Roland Garros 2025 defeating Sinner. He is a young champion who is very talented."*

**Scores:** Faithfulness: 0.250 | Relevance: 0.286 | Completeness: 0.143 | Overall: **0.226**

**5 Whys Analysis:**
| Level | Question | Answer |
|-------|----------|--------|
| Symptom | Vấn đề là gì? | Score gần lowest (0.226) — agent bỏ sót hoàn toàn các yếu tố lịch sử quan trọng |
| Why 1 | Tại sao Completeness = 0.143? | Expected answer đề cập 4 điểm lịch sử cụ thể (bảo vệ chức vô địch lần 3, ngược dòng từ 0-2, 5-0 Grand Slam finals, trận chung kết dài nhất) — agent chỉ cover 1/4 |
| Why 2 | Tại sao agent bỏ sót? | Mock agent chỉ match keyword "Roland Garros" + "Alcaraz" nhưng không có khả năng tổng hợp thông tin lịch sử từ context đa câu |
| Why 3 | Tại sao Faithfulness thấp (0.250)? | Agent dùng "very talented" không có trong context; context có "longest final in Roland Garros history" nhưng agent không trích dẫn |
| Why 4 | Root cause là gì? | Agent không có khả năng tổng hợp nhiều facts từ context phức tạp — chỉ lấy surface-level information |

**Root cause (from `find_root_cause()`):**
> *"Answer is missing key information — increase context window or improve generation"* (do Completeness thấp nhất)

**Bạn có đồng ý với root cause suggestion không? Tại sao?**
> **Một phần.** Root cause là đúng — agent thiếu khả năng multi-fact synthesis. Nhưng "increase context window" không đủ vì context đã có đầy đủ thông tin; vấn đề là generation không khai thác được context. Root cause thực sự sâu hơn: cần **instruction tuning** để agent trả lời câu hỏi dạng "historical significance" bằng cách enumerate các khía cạnh lịch sử riêng biệt.

**Proposed fix:**
> 1. Thêm few-shot examples trong prompt cho câu hỏi dạng "significance/historical" — chỉ rõ agent phải liệt kê từng yếu tố một với evidence từ context
> 2. Thêm instruction: "For questions asking about significance/importance, enumerate each factor separately with specific data from the context"

---

### Failure 2

**Question:** *What does Roland Garros 2026 reveal about the state of generational change in men's tennis?*

**Agent Answer:** *"Tennis is changing with new players emerging at Roland Garros 2026."*

**Scores:** Faithfulness: 0.229 | Relevance: 0.278 | Completeness: 0.446 | Overall: **0.318**

**5 Whys Analysis:**
| Level | Question | Answer |
|-------|----------|--------|
| Symptom | Vấn đề là gì? | Score 0.318 — câu trả lời quá chung chung, thiếu tên cầu thủ và sự kiện cụ thể |
| Why 1 | Tại sao Faithfulness = 0.229? | Agent dùng "tennis is changing" — phrase này không có trong context (context có "chứng kiến nhiều tên tuổi lớn sớm dừng bước", "Fonseca", "Cirstea") |
| Why 2 | Tại sao agent không lấy tên cầu thủ từ context? | Mock agent không phân biệt được proper nouns cần được extracted — chỉ match general sports terms |
| Why 3 | Tại sao Relevance thấp (0.278)? | Câu hỏi chứa "generational change" — agent không dùng từ này hay synonym (generation, era, transition) |
| Why 4 | Root cause là gì? | Agent thiếu entity extraction — không recognize rằng tên cầu thủ (Fonseca, Cirstea) là thông tin bắt buộc phải include khi trả lời câu hỏi về "ai đại diện thế hệ mới" |

**Root cause:**
> Context is missing or irrelevant — improve retrieval *(do Faithfulness thấp nhất)*

**Proposed fix:**
> 1. Entity extraction: trước khi generate, extract proper nouns từ context (tên cầu thủ, giải đấu, số liệu) → inject vào prompt như "Key entities to mention: Fonseca, Cirstea, GQ"
> 2. Thêm constraint trong prompt: "Your answer must mention specific player names and events from the context — general statements are not acceptable"

---

### Failure 3

**Question:** *Is Cristiano Ronaldo better than Lionel Messi based on their World Cup 2026 performances so far?*

**Agent Answer:** *"Ronaldo has more World Cup goals and has performed better historically. Messi won the 2022 World Cup which is his greatest achievement."*

**Scores:** Faithfulness: 0.192 | Relevance: 0.385 | Completeness: 0.426 | Overall: **0.334**

**5 Whys Analysis:**
| Level | Question | Answer |
|-------|----------|--------|
| Symptom | Vấn đề là gì? | Score 0.334 — agent hallucinate thông tin World Cup 2026 performance không có trong context |
| Why 1 | Tại sao Faithfulness = 0.192? | Agent claim "Ronaldo has more World Cup goals" — không có trong context (context chỉ nói Ronaldo dự WC thứ 6 ở tuổi 41, không có match statistics) |
| Why 2 | Tại sao agent hallucinate? | Câu hỏi adversarial dùng "World Cup 2026 performances" nhưng không có match data → agent fallback to parametric knowledge (training data về Ronaldo/Messi) |
| Why 3 | Tại sao không detect out-of-scope? | Mock agent không có mechanism để detect khi context không đủ để trả lời câu hỏi → không "từ chối có lý do" |
| Why 4 | Root cause là gì? | Agent thiếu grounding check — không so sánh câu hỏi với available context trước khi generate, không phát hiện "không có performance data để trả lời" |

**Root cause:**
> Answer does not address the question — improve prompt clarity *(do Relevance thấp nhất)*

**Proposed fix:**
> 1. Pre-generation grounding check: kiểm tra xem context có đủ thông tin để trả lời câu hỏi không; nếu không → generate "refusal với lý do" thay vì hallucinate
> 2. Adversarial prompt template: "If the context does not contain match statistics or performance data for the event mentioned in the question, clearly state this and do NOT use prior knowledge"

---

## 3. Failure Clustering

Theo bài giảng: "Fix 1 root cause giải quyết nhiều failures cùng lúc."

**Cluster Analysis:**

| Cluster | Root Cause | Failures in cluster | Priority |
|---------|-----------|--------------------:|----------|
| 1 — Hallucination | Agent dùng parametric knowledge khi context không đủ → tạo sự kiện không có trong context | H02, H03, H04, H05, A01, A03, M04 (7 failures) | High |
| 2 — Off-topic/Relevance Gap | Word-overlap metric + agent không mirror từ câu hỏi về answer → Relevance thấp mặc dù nội dung đúng | E03, E04, E05, M01, M03, M05, M06, A02 (8 failures) | High |
| 3 — Irrelevant | Agent trả lời không đúng khía cạnh câu hỏi, bỏ sót key details | M02, M07, H01 (3 failures) | Medium |

**Nếu chỉ fix 1 cluster, bạn chọn cluster nào? Tại sao?**
> **Cluster 1 — Hallucination** vì nó ảnh hưởng đến 7/18 failures (38.9%) và là nguyên nhân của các worst scores (H02=0.226, H05=0.318, A03=0.334). Hallucination là failure type nguy hiểm nhất trong sports domain vì thông tin sai (kết quả trận đấu, số liệu thống kê) gây mất tin tưởng người dùng ngay lập tức. Fix bằng grounding check trước khi generate: kiểm tra xem context có đủ evidence không, nếu không → từ chối có lý do thay vì hallucinate.

---

## 4. Improvement Log (from `generate_improvement_log`)

Paste output của `generate_improvement_log()`:

```
| Failure ID | Type | Root Cause | Suggested Fix | Status |
|------------|------|------------|---------------|--------|
| F001 | hallucination | Answer is missing key information — increase context window or improve generation | Implement hallucination checker to filter unsupported claims | Open |
| F002 | off_topic | Answer does not address the question — improve prompt clarity | Improve prompt clarity to ensure answer addresses the question directly | Open |
| F003 | irrelevant | Answer does not address the question — improve prompt clarity | Increase chunk size in RAG pipeline to reduce context fragmentation | Open |
| F004 | hallucination | Answer is missing key information — increase context window or improve generation | Add intent detection to route queries to appropriate handlers | Open |
| F005 | off_topic | Answer is missing key information — increase context window or improve generation | Review manually | Open |
| F006 | hallucination | Context is missing or irrelevant — improve retrieval | Review manually | Open |
| F007 | irrelevant | Answer does not address the question — improve prompt clarity | Review manually | Open |
| F008 | off_topic | Answer does not address the question — improve prompt clarity | Review manually | Open |
| F009 | hallucination | Context is missing or irrelevant — improve retrieval | Review manually | Open |
| F010 | off_topic | Answer is missing key information — increase context window or improve generation | Review manually | Open |
```

**Thêm 3 improvement suggestions từ `generate_improvement_suggestions()`:**
1. Implement hallucination checker to filter unsupported claims
2. Improve prompt clarity to ensure answer addresses the question directly
3. Increase chunk size in RAG pipeline to reduce context fragmentation
4. Add grounding check: if context lacks required data → generate refusal instead of hallucinating *(bonus — từ hallucination cluster)*

---

## 5. Regression Testing Strategy

### CI/CD Integration

**Câu 1: Khi nào chạy `run_regression()` trong production system?**
> Chạy `run_regression()` tại **3 điểm trong CI/CD flow**:
> - **Trước mỗi merge to main**: so sánh branch mới vs baseline (main HEAD) — block merge nếu regression
> - **Sau mỗi prompt change hoặc model upgrade**: dù không thay code, prompt/model mới có thể affect scores
> - **Sau khi update knowledge base/RAG index**: nội dung thể thao mới (ví dụ kết quả World Cup, NBA playoffs) có thể ảnh hưởng retrieval và faithfulness

**Câu 2: Threshold regression 0.05 có phù hợp domain của bạn không?**
> Với domain Sports News, **0.05 là hợp lý nhưng nên strict hơn cho Faithfulness** (ngưỡng 0.03). Lý do: người dùng kiểm tra kết quả trận đấu, số liệu thống kê — sai số nhỏ 5% trong faithfulness có thể dẫn đến thông tin sai về tỷ số, tên cầu thủ. Đây là critical trong sports reporting. Cho Completeness và Relevance, 0.05 là đủ vì đây là heuristic metric với nhiều false negatives (đặc biệt với dữ liệu đa ngôn ngữ).

**Câu 3: Khi phát hiện regression — block deployment hay chỉ alert?**
> **Tiered approach**:
> - **Block deploy** nếu: Faithfulness drop > 0.03 (hallucination risk — sai kết quả trận đấu), hoặc Overall Score drop > 0.05 vs baseline
> - **Alert + require approval** nếu: Relevance hoặc Completeness drop > 0.05 (quality degradation nhưng không critical)
> - **Log only** nếu: drop < 0.03 trên bất kỳ metric (noise trong evaluation)
>
> Trade-off: Block quá nhiều = team friction; Block quá ít = sports facts sai được deploy. Tiered approach cân bằng safety vs velocity.

**Câu 4: Eval pipeline nên chạy ở đâu trong CI/CD flow?**

```
Code change → [Unit tests + Fast Eval] → [Full Benchmark + Regression] → [Human Spot-check] → Deploy
              (bước 1)                    (bước 2)                         (bước 3)
```
> - **Bước 1** (mỗi commit, ~2 phút): `pytest tests/ -v` + fast eval trên 5 easy QA pairs (E01–E05) — fail fast
> - **Bước 2** (mỗi PR merge, ~15 phút): Full 20 QA benchmark + `run_regression()` vs baseline — block deploy nếu fail
> - **Bước 3** (weekly hoặc trước mùa giải mới, ~1 giờ): Human review 5% sample + LLM-as-judge trên full golden dataset

---

## 6. Continuous Improvement Loop

Theo bài giảng: Evaluate → Analyze → Improve → Augment (add to benchmark) → lặp lại

**Sau lab hôm nay, 3 actions tiếp theo bạn sẽ làm để improve agent:**

| Priority | Action | Metric sẽ improve | Expected impact |
|----------|--------|-------------------|-----------------|
| 1 | Implement grounding check: trước khi generate, verify context có đủ thông tin không; nếu không → generate refusal thay vì hallucinate | Faithfulness (0.412 → dự kiến > 0.65) | Loại bỏ 7 hallucination failures (H02–H05, A01, A03, M04) — biggest cluster |
| 2 | Thay word-overlap Relevance metric bằng multilingual embedding similarity (dùng `multilingual-e5-base`) | Relevance (0.467 → dự kiến > 0.70) | Xử lý mismatch tiếng Anh/Việt; loại bỏ false negatives trong off_topic cluster |
| 3 | Thêm entity extraction pass trước generation: extract tên cầu thủ, số liệu, sự kiện từ context → inject vào prompt | Completeness (0.603 → dự kiến > 0.75) | Agent không bỏ sót proper nouns quan trọng trong câu trả lời sports |

**Bạn sẽ thêm failure cases nào vào benchmark cho sprint tiếp theo?**
> 1. **Live result queries** — câu hỏi về kết quả trận đấu đang diễn ra mà knowledge base chưa cập nhật (ví dụ: "What was the score in Game 2 of the 2026 NBA Finals?"). Cần test xem agent từ chối đúng cách hay hallucinate kết quả.
> 2. **Multi-language switching** — câu hỏi tiếng Anh nhưng context chỉ có tiếng Việt và ngược lại. Hiện tại word-overlap metric bị affected nặng bởi cross-language mismatch.
> 3. **Statistical comparison cases** — câu hỏi so sánh số liệu của 2 cầu thủ/đội (ví dụ: "Who had more assists per game: SGA or Brunson in 2025 playoffs?") — cần table lookup reasoning không có trong context đơn lẻ.

---

## 7. Framework Reflection

**Framework bạn đã dùng trong lab:** RAGAS-inspired word-overlap heuristic (custom implementation)

**Nếu dùng trong production, bạn sẽ chọn framework nào? Tại sao?**

> **Chọn DeepEval** với lý do chính là CI/CD integration tốt nhất cho team development workflow, cộng với khả năng detect hallucination quan trọng cho sports domain.

| Tiêu chí | Lý do chọn |
|----------|------------|
| Focus phù hợp vì... | DeepEval có HallucinationMetric riêng (quan trọng nhất với sports domain — không thể có facts sai) cộng thêm FaithfulnessMetric và AnswerRelevancyMetric |
| CI/CD integration vì... | `deepeval test run test_eval.py` chạy native trong pytest — không cần custom CI script; dễ integrate vào GitHub Actions trong 1 job step |
| Multilingual support vì... | DeepEval dùng LLM-as-judge (GPT-4) thay vì word-overlap → xử lý được mismatch tiếng Anh/Việt trong sports content — critical cho dataset thực tế của project này |
