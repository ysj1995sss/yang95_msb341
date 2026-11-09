import { describe, expect, it } from "vitest";
import { categories } from "./data/categories";
import { dailyQuestions } from "./data/dailyQuestions";
import { guessQuestions, guessThemes } from "./data/guessQuestions";
import { questionById, questions, questionsFor } from "./data/questions";

const norm = (text: string) => text.trim().toLowerCase().replace(/\s+/g, " ");

// Words that carry no meaning of their own, so two questions aren't "alike" just for sharing them.
const FILLER = new Set(
  ("a an the and or of to in on at for with from by is are was were be been it its this that these those you your " +
    "yours we our us they their them he she his her i me my what whats how who which when where why do does did " +
    "would could should can will ever one thing something someone about if than then so as not no yes more most " +
    "rather dare truth never have has had get got you're you've you'd you'll it's that's there's").split(" "),
);
const words = (text: string) =>
  new Set(norm(text).replace(/[^a-z0-9' ]/g, " ").split(" ").map((w) => w.replace(/'s$/, "")).filter((w) => w.length > 2 && !FILLER.has(w)));
/** Shared meaningful words over all meaningful words in either question (1 = the same words). */
function similarity(a: string, b: string): number {
  const x = words(a);
  const y = words(b);
  const shared = [...x].filter((w) => y.has(w)).length;
  return shared / Math.max(1, new Set([...x, ...y]).size);
}

describe("the library", () => {
  it("has the ten experiences, each with a unique id", () => {
    expect(categories).toHaveLength(10);
    expect(new Set(categories.map((c) => c.id)).size).toBe(10);
  });

  it("holds exactly 500 questions, exactly 50 in each category", () => {
    expect(questions).toHaveLength(500);
    for (const category of categories) {
      expect(questionsFor(category.id), category.name).toHaveLength(50);
    }
  });

  it("gives every question a unique, stable-looking id and real text", () => {
    const ids = questions.map((q) => q.id);
    expect(new Set(ids).size).toBe(500);
    for (const q of questions) {
      expect(q.id).toMatch(new RegExp(`^${q.categoryId}-\\d+$`));
      expect(questionById(q.id)).toBe(q);
    }
  });

  it("keeps the ids that questions had before this sprint, so nothing saved is lost", () => {
    const before: [string, string][] = [
      ["love-1", "What's something you've always wanted to experience with your partner?"],
      ["love-12", "What does a lazy Sunday together look like in your dream version?"],
      ["deep-1", "What's one belief you've changed your mind about?"],
      ["deep-12", "How do you want people to feel after spending time with you?"],
      ["party-1", "What's the most embarrassing thing you've ever done?"],
      ["party-12", "Who here is most likely to become famous, and for what?"],
      ["debate-1", "Should couples share their phone passwords?"],
      ["debate-12", "Is it rude to text at the dinner table?"],
      ["family-1", "What's your favorite childhood memory?"],
      ["family-12", "What toy or game did you love most as a kid?"],
      ["icebreakers-1", "What's something interesting about you that most people don't know?"],
      ["icebreakers-12", "What's one app you couldn't live without?"],
      ["would-you-rather-1", "Would you rather travel 100 years into the past or 100 years into the future?"],
      ["would-you-rather-12", "Would you rather relive your best day or skip your worst one?"],
      ["imagination-1", "If you could invent one thing that doesn't exist, what would it be?"],
      ["imagination-12", "If the weather matched people's moods, what would today's forecast be?"],
      ["storytelling-1", "Tell us about a time when everything went completely wrong."],
      ["storytelling-12", "Tell us about a moment you knew you'd made the right choice."],
      ["trivia-1", "What is the largest ocean on Earth?"],
      ["trivia-8", "Which 1997 film was the first to earn more than $1 billion at the box office worldwide?"],
      ["trivia-12", "Which city's wall fell in 1989, opening the way to German reunification?"],
    ];
    for (const [id, text] of before) expect(questionById(id)?.text, id).toBe(text);
  });

  it("is written cleanly: capitalized, punctuated, no stray spaces, a sensible length", () => {
    for (const q of questions) {
      expect(q.text, q.id).toBe(q.text.trim());
      expect(q.text, q.id).not.toMatch(/\s{2,}/);
      expect(q.text[0], q.id).toBe(q.text[0].toUpperCase());
      expect(q.text, q.id).toMatch(/[?.!]$/);
      expect(q.text.length, q.id).toBeGreaterThan(14);
      expect(q.text.length, q.id).toBeLessThan(170);
    }
  });

  it("never repeats a question, in the library or the daily list", () => {
    const all = [...questions.map((q) => q.text), ...dailyQuestions.map((d) => d.text)].map(norm);
    expect(new Set(all).size).toBe(all.length);
  });

  it("has no near-duplicates: no two questions share nearly all their meaningful words", () => {
    const all = [...questions.map((q) => ({ id: q.id, text: q.text })), ...dailyQuestions.map((d) => ({ id: d.id, text: d.text }))];
    const alike: string[] = [];
    for (let i = 0; i < all.length; i++) {
      for (let j = i + 1; j < all.length; j++) {
        if (words(all[i].text).size >= 3 && words(all[j].text).size >= 3 && similarity(all[i].text, all[j].text) >= 0.5) {
          alike.push(`${all[i].id} ~ ${all[j].id}: "${all[i].text}" / "${all[j].text}"`);
        }
      }
    }
    expect(alike).toEqual([]);
  });

  it("doesn't lean on one sentence shape: no opening of two words starts more than a third of a category", () => {
    for (const category of categories) {
      if (category.id === "trivia") continue;
      const counts = new Map<string, number>();
      for (const q of questionsFor(category.id)) {
        const opening = norm(q.text).split(" ").slice(0, 2).join(" ");
        counts.set(opening, (counts.get(opening) ?? 0) + 1);
      }
      const [top, n] = [...counts.entries()].sort((a, b) => b[1] - a[1])[0];
      // "Would you" is the point of the Would You Rather category, which mixes in dilemmas instead.
      const limit = category.id === "would-you-rather" ? 32 : 17;
      expect(n, `${category.name}: "${top}"`).toBeLessThanOrEqual(limit);
    }
    const dilemmas = questionsFor("would-you-rather").filter((q) => !/^would you rather/i.test(q.text));
    expect(dilemmas.length).toBeGreaterThanOrEqual(15);
  });
});

describe("depth levels", () => {
  it("spreads each category across all four levels, about evenly", () => {
    for (const category of categories) {
      for (const depth of [1, 2, 3, 4]) {
        const n = questionsFor(category.id).filter((q) => q.depth === depth).length;
        expect(n, `${category.name} level ${depth}`).toBeGreaterThanOrEqual(11);
        expect(n, `${category.name} level ${depth}`).toBeLessThanOrEqual(14);
      }
    }
  });
});

describe("trivia", () => {
  const trivia = questionsFor("trivia");

  it("gives every question four different options, one valid answer and an explanation", () => {
    for (const q of trivia) {
      if (q.kind !== "trivia") throw new Error(`${q.id} is not a trivia question`);
      expect(new Set(q.options.map(norm)).size, q.text).toBe(4);
      expect([0, 1, 2, 3]).toContain(q.answer);
      expect(q.explanation.length, q.text).toBeGreaterThan(20);
      expect(q.explanation, q.text).toMatch(/[.!]$/);
      expect(q.topic).toBeTruthy();
    }
    expect(questions.every((q) => (q.categoryId === "trivia") === (q.kind === "trivia"))).toBe(true);
  });

  it("covers geography, history, science, entertainment, culture, logic and general knowledge", () => {
    const topics = new Set(trivia.map((q) => (q.kind === "trivia" ? q.topic : "")));
    for (const topic of ["Geography", "History", "Science", "Entertainment", "Culture", "Logic", "General knowledge"]) {
      expect(topics.has(topic as never), topic).toBe(true);
    }
  });

  it("doesn't hide the right answer in one spot", () => {
    const where = [0, 0, 0, 0];
    for (const q of trivia) if (q.kind === "trivia") where[q.answer]++;
    for (const n of where) expect(n).toBeGreaterThanOrEqual(8);
  });
});

describe("Guess My Answer questions", () => {
  it("has a set for each theme, with four different answers each", () => {
    expect(guessQuestions.length).toBeGreaterThanOrEqual(60);
    expect(new Set(guessQuestions.map((q) => q.id)).size).toBe(guessQuestions.length);
    expect(new Set(guessQuestions.map((q) => norm(q.text))).size).toBe(guessQuestions.length);
    for (const theme of guessThemes) {
      expect(guessQuestions.filter((q) => q.themeId === theme.id).length, theme.name).toBeGreaterThanOrEqual(10);
    }
    for (const q of guessQuestions) {
      expect(new Set(q.options.map(norm)).size, q.id).toBe(4);
      expect(q.text, q.id).toMatch(/\?$/);
    }
  });
});

describe("daily question", () => {
  it("has a month of daily questions", () => {
    expect(dailyQuestions.length).toBeGreaterThanOrEqual(30);
  });
});
