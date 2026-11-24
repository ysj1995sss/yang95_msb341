import type { Depth, TriviaQuestion, TriviaTopic } from "../../types";
import { culture } from "./culture";
import { food } from "./food";
import { geography } from "./geography";
import { history } from "./history";
import { logic } from "./logic";
import { music } from "./music";
import { science } from "./science";
import { screen } from "./screen";
import { sports } from "./sports";
import { tech } from "./tech";

// The trivia bank: one file per area, one question per line:
//   difficulty | question | right answer | wrong | wrong | wrong | explanation | Wikipedia article
// A question's id is its area and its line ("trivia-food-12"), so add new lines at the END of a file;
// never insert, reorder or delete a line, or saved favorites would point at another question.
// The right answer is written first and moved to a fixed, spread-out position when the file is read.
const files: readonly [id: string, topic: TriviaTopic, lines: string][] = [
  ["geography", "Geography", geography],
  ["history", "History", history],
  ["science", "Science", science],
  ["screen", "Movies & TV", screen],
  ["music", "Music & entertainment", music],
  ["sports", "Sports & games", sports],
  ["food", "Food & drink", food],
  ["culture", "Art, books & culture", culture],
  ["tech", "Technology", tech],
  ["logic", "General & logic", logic],
];

function parse(id: string, topic: TriviaTopic, line: string, i: number): TriviaQuestion {
  const [level, text, right, a, b, c, explanation, source] = line.split("|") as [string, string, string, string, string, string, string, string];
  const answer = ((i * 7 + text.length) % 4) as 0 | 1 | 2 | 3;
  const options = [a, b, c];
  options.splice(answer, 0, right);
  return {
    id: `trivia-${id}-${i + 1}`, categoryId: "trivia", kind: "trivia", depth: Number(level) as Depth,
    topic, source, text, options: options as unknown as TriviaQuestion["options"], answer, explanation,
  };
}

export const triviaBank: TriviaQuestion[] = files.flatMap(([id, topic, lines]) =>
  lines.trim().split("\n").map((line, i) => parse(id, topic, line, i)));

export const sourceUrl = (q: Pick<TriviaQuestion, "source">): string =>
  `https://en.wikipedia.org/wiki/${encodeURIComponent(q.source.replace(/ /g, "_"))}`;
