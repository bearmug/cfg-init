import { readFile } from "node:fs/promises";

interface Fixture {
  id: string;
  domain: string;
  tags: string[];
  questions: Record<string, { type: "choice" | "noul" | "score"; criteria?: Record<string, unknown> | unknown[] }>;
  expected: Record<string, string | number>;
}
interface Result {
  id: string;
  selector?: string;
  model: string;
  native?: boolean;
  api?: string;
  answers?: Record<string, { type?: string; choice?: string; noul?: number; score?: number;
    probabilities?: Record<string, number>; confidence?: number }>;
  elapsedMs: number;
  error?: string;
  usage?: { cost?: { total: number }; truncated?: boolean; state_tokens_dropped?: number };
}
const jsonl = async <T>(path: string): Promise<T[]> =>
  (await readFile(path, "utf8")).trim().split("\n").filter(Boolean).map((line: string) => JSON.parse(line));
const [fixturePath, ...paths] = process.argv.slice(2);
if (!fixturePath || paths.length === 0) throw new Error("Usage: bun score.ts fixtures.jsonl result.jsonl [result.jsonl ...]");
const fixtures = await jsonl<Fixture>(fixturePath);
const byId = new Map(fixtures.map(fixture => [fixture.id, fixture]));
if (byId.size !== fixtures.length) throw new Error("Duplicate fixture id");
const results = (await Promise.all(paths.map((path: string) => jsonl<Result>(path)))).flat();
const groups = new Map<string, Result[]>();
for (const result of results) {
  if (!byId.has(result.id)) throw new Error(`Unknown result id ${result.id}`);
  const key = result.selector ?? result.model;
  const group = groups.get(key) ?? [];
  group.push(result);
  groups.set(key, group);
}
const quantile = (values: number[], q: number): number | null => {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.max(0, Math.ceil(q * sorted.length) - 1)];
};
const mean = (values: number[]): number | null => values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
const probability = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1;
const summaries = [];
for (const [selector, rows] of groups) {
  const native = rows.every(row => row.native !== false && (row.native === true || row.api === "typesafe"));
  const lookup = new Map(rows.map(row => [row.id, row]));
  if (lookup.size !== rows.length) throw new Error(`Duplicate result ids for ${selector}`);
  let correct = 0;
  let questions = 0;
  let schemaFailures = 0;
  const domains: Record<string, { correct: number; total: number }> = {};
  const errors: unknown[] = [];
  const misses: unknown[] = [];
  const calibration: Array<{ confidence: number; correct: number }> = [];
  const brier: Record<string, number[]> = { choice: [], noul: [], score: [] };
  const scoreErrors: number[] = [];
  const confusion: Record<string, Record<string, Record<string, number>>> = {};
  for (const fixture of fixtures) {
    const row = lookup.get(fixture.id);
    if (!row || row.error) errors.push({ id: fixture.id, error: row?.error ?? "missing result" });
    const domain = domains[fixture.domain] ??= { correct: 0, total: 0 };
    for (const [id, expected] of Object.entries(fixture.expected)) {
      questions++;
      domain.total++;
      const question = fixture.questions[id];
      const answer = row?.answers?.[id];
      let predicted: string | number | undefined;
      let valid = !!answer && (!answer.type || answer.type === question.type);
      if (question.type === "noul") {
        valid = valid && probability(answer?.noul);
        if (valid) {
          const p = answer!.noul!;
          predicted = p >= 0.5 ? 1 : 0;
          brier.noul.push((p - Number(expected)) ** 2);
          calibration.push({ confidence: Math.max(p, 1 - p), correct: Number(predicted === expected) });
        }
      } else {
        const labels = question.type === "choice" ? Object.keys(question.criteria!) : (question.criteria as unknown[]).map((_, i) => String(i));
        const probabilities = answer?.probabilities;
        valid = valid && !!probabilities && Object.keys(probabilities!).length === labels.length &&
          labels.every(label => probability(probabilities![label])) &&
          Math.abs(labels.reduce((sum, label) => sum + probabilities![label], 0) - 1) <= 0.002;
        if (question.type === "choice") {
          valid = valid && typeof answer?.choice === "string" && labels.includes(answer.choice);
          if (valid) {
            predicted = answer!.choice!;
            calibration.push({ confidence: probabilities![predicted], correct: Number(predicted === expected) });
            const table = confusion[fixture.domain] ??= {};
            const expectedRow = table[String(expected)] ??= {};
            expectedRow[String(predicted)] = (expectedRow[String(predicted)] ?? 0) + 1;
          }
        } else {
          valid = valid && typeof answer?.score === "number" && Number.isFinite(answer.score) &&
            answer.score >= 0 && answer.score <= labels.length - 1;
          if (valid) {
            predicted = Math.round(answer!.score!);
            scoreErrors.push(Math.abs(answer!.score! - Number(expected)));
          }
        }
        if (valid) brier[question.type].push(labels.reduce((sum, label) =>
          sum + (probabilities![label] - Number(label === String(expected))) ** 2, 0));
      }
      if (!valid) schemaFailures++;
      if (valid && predicted === expected) { correct++; domain.correct++; }
      else misses.push({ id: fixture.id, question: id, expected, predicted, valid, answer, tags: fixture.tags,
        truncated: row?.usage?.truncated ?? false });
    }
  }
  const bins = Array.from({ length: 10 }, () => [] as typeof calibration);
  for (const item of calibration) bins[Math.min(9, Math.floor(item.confidence * 10))].push(item);
  const ece = calibration.length ? bins.reduce((sum, bin) => !bin.length ? sum :
    sum + bin.length / calibration.length * Math.abs(mean(bin.map(x => x.confidence))! - mean(bin.map(x => x.correct))!), 0) : null;
  const nativeCoverage = [0.5, 0.7, 0.9].map(threshold => {
    const accepted = calibration.filter(item => item.confidence >= threshold);
    return { threshold, coverage: accepted.length / (calibration.length || 1), accuracy: mean(accepted.map(item => item.correct)) };
  });
  const macroF1: Record<string, number | null> = {};
  for (const [domain, table] of Object.entries(confusion)) {
    const labels = [...new Set(fixtures.filter(f => f.domain === domain).flatMap(f =>
      Object.values(f.questions).filter(q => q.type === "choice").flatMap(q => Object.keys(q.criteria!))))];
    macroF1[domain] = mean(labels.map(label => {
      const tp = table[label]?.[label] ?? 0;
      const fp = Object.entries(table).filter(([expected]) => expected !== label).reduce((sum, [, values]) => sum + (values[label] ?? 0), 0);
      const fn = Object.entries(table[label] ?? {}).filter(([predicted]) => predicted !== label).reduce((sum, [, n]) => sum + n, 0);
      return 2 * tp + fp + fn ? 2 * tp / (2 * tp + fp + fn) : 0;
    }));
  }
  const priced = rows.filter(row => row.usage?.cost?.total !== undefined);
  summaries.push({ selector, native, fixtures: fixtures.length, received: rows.length,
    questions, correct, accuracy: correct / questions, schemaFailures, requestErrors: errors,
    domains, macroF1, latencyMs: { p50: quantile(rows.map(row => row.elapsedMs), 0.5), p95: quantile(rows.map(row => row.elapsedMs), 0.95) },
    reportedCostUsd: priced.length ? priced.reduce((sum, row) => sum + row.usage!.cost!.total, 0) : null,
    calibration: native ? { ece10Bins: ece, brier: Object.fromEntries(Object.entries(brier).map(([type, values]) => [type, mean(values)])),
      decisionCoverage: nativeCoverage } : { unavailable: "Prompted adapter returns synthetic one-hot probabilities, not calibrated confidence" },
    scoreMeanAbsoluteError: mean(scoreErrors), truncatedStates: rows.filter(row => row.usage?.truncated).map(row => row.id), misses });
}
console.log(JSON.stringify({ fixtureCount: fixtures.length, questionCount: fixtures.reduce((n, f) => n + Object.keys(f.expected).length, 0),
  methodology: "Fixed manual synthetic held-out fixtures; no training/tuning. Decision accuracy: choice exact, noul >=0.5, score rounded to nearest level. Calibration is diagnostic on this small sample, not production validation. Multiclass Brier is summed squared error; binary Brier is squared yes-probability error. ECE uses predicted class probability, not the API confidence field. Latency protocols must be compared separately.", summaries }, null, 2));
