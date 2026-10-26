import { describe, expect, it } from "vitest";
import { categories } from "./data/categories";
import { dailyQuestions } from "./data/dailyQuestions";
import { questions, questionsFor } from "./data/questions";

const norm = (text: string) => text.trim().toLowerCase().replace(/\s+/g, " ");

describe("question content", () => {
  it("has the ten experiences, each with a unique id", () => {
    expect(categories).toHaveLength(10);
    expect(new Set(categories.map((c) => c.id)).size).toBe(10);
  });

  it("gives every category at least 10 questions, 100 or more in all", () => {
    for (const category of categories) {
      expect(questionsFor(category.id).length, category.name).toBeGreaterThanOrEqual(10);
    }
    expect(questions.length).toBeGreaterThanOrEqual(100);
  });

  it("never repeats a question, across categories or in the daily list", () => {
    const all = [...questions.map((q) => q.text), ...dailyQuestions.map((d) => d.text)].map(norm);
    expect(new Set(all).size).toBe(all.length);
    const ids = [...questions.map((q) => q.id), ...dailyQuestions.map((d) => d.id)];
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("gives every trivia question four different options, one answer and an explanation", () => {
    const trivia = questions.filter((q) => q.kind === "trivia");
    expect(trivia.length).toBeGreaterThanOrEqual(10);
    for (const q of trivia) {
      expect(new Set(q.options.map(norm)).size, q.text).toBe(4);
      expect([0, 1, 2, 3]).toContain(q.answer);
      expect(q.explanation.length, q.text).toBeGreaterThan(10);
    }
    // Only the trivia category has multiple-choice questions.
    expect(questions.every((q) => (q.categoryId === "trivia") === (q.kind === "trivia"))).toBe(true);
  });

  it("has a month of daily questions", () => {
    expect(dailyQuestions.length).toBeGreaterThanOrEqual(30);
  });
});
