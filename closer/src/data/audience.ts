import type { Audience, AudienceChoice, Depth, OpenQuestion, Question } from "../types";
import { createSetting } from "../utils/settings";
import { questions } from "./questions";

// Relationship-type tags: which groups a question suits. Every question is tagged from rules, so the
// tagging stays consistent as questions are added:
//   1. each category starts from the groups it is written for;
//   2. the more personal a question gets, the narrower the group (a Bold question suits couples and
//      close friends, not a team meeting);
//   3. what the words say then adjusts it: "partner" is for couples, "your manager" for teams,
//      "your parents" for families, "this group" needs more than two people.
// Trivia is for everyone.

export const AUDIENCES: readonly { id: Audience; label: string; blurb: string }[] = [
  { id: "couple", label: "Couples", blurb: "Date night and getting closer" },
  { id: "friends", label: "Friends", blurb: "Hangouts, road trips and group chats" },
  { id: "family", label: "Family", blurb: "Dinner tables and holidays" },
  { id: "team", label: "Teams", blurb: "Meetings, offsites and new colleagues" },
];

export const ALL_AUDIENCES: readonly Audience[] = ["couple", "friends", "family", "team"];

export const isAudience = (value: unknown): value is Audience => ALL_AUDIENCES.includes(value as Audience);

const ladder: Record<Depth, readonly Audience[]> = {
  1: ALL_AUDIENCES,
  2: ALL_AUDIENCES,
  3: ["couple", "friends", "family"],
  4: ["couple", "friends"],
};

const base: Record<string, readonly Audience[]> = {
  love: ["couple"],
  deep: ALL_AUDIENCES,
  party: ["friends", "couple", "family", "team"],
  debate: ALL_AUDIENCES,
  family: ["family", "couple", "friends", "team"],
  icebreakers: ["team", "friends", "family", "couple"],
  "would-you-rather": ALL_AUDIENCES,
  imagination: ALL_AUDIENCES,
  storytelling: ALL_AUDIENCES,
  pack: ALL_AUDIENCES,
  mine: ALL_AUDIENCES,
};

const romantic = /\b(partner|spouse|husband|wife|boyfriend|girlfriend|flirt\w*|romantic|kiss\w*|attractive|date night|perfect date|double-date|anniversary|couples?)\b/i;
const relationship = /\b(relationship|ex-partners?|dating|a date|crush)\b/i;
const work = /\b(work|coworker|colleague|boss|manager|team|teammate|meetings|career|job|professional|professionally|promotion|office|leader|collaboration)\b/i;
const workplace = /\b(work|coworker|colleague|boss|manager|team|teammate|meeting|meetings|leader|collaboration|professionally)\b/i;
const familyWords = /\b(parents?|mom|dad|mother|father|grandparents?|grandma|grandpa|siblings?|brothers?|sisters?|family|ancestors?|relatives?|childhood|kids?|child|teenagers?)\b/i;
const groupWords = /\b(this group|this room|the group|the room|who here|who in)\b/i;
const friendGroup = /\bfriend group\b|\bwho in your friend/i;

export function audiencesOfEntry(categoryId: string, depth: Depth, text: string): readonly Audience[] {
  if (categoryId === "trivia") return ALL_AUDIENCES;
  let tags = new Set((base[categoryId] ?? ALL_AUDIENCES).filter((a) => ladder[depth].includes(a)));
  const add = (...list: Audience[]) => list.forEach((a) => tags.add(a));
  const keep = (...list: Audience[]) => { tags = new Set([...tags].filter((a) => list.includes(a))); };

  // A category always suits the group it is named for, whatever the depth.
  if (categoryId === "family") add("family", "couple", "friends");
  if (categoryId === "love") add("couple");
  if (categoryId === "icebreakers") add("team");

  // Love questions with no partner in them suit anyone close to you.
  if (categoryId === "love" && depth <= 3 && !romantic.test(text) && !relationship.test(text) && !/\b(me|we|us|our)\b/i.test(text)) add("friends", "family");

  if (romantic.test(text) || relationship.test(text)) {
    // About a partner: couples; in debates and dilemmas, friends talk about it too.
    if (romantic.test(text) && categoryId !== "debate" && categoryId !== "would-you-rather") keep("couple");
    else keep("couple", "friends");
    add("couple");
  } else if (work.test(text)) {
    // About work: a team (an icebreaker that is clearly about the workplace is only for teams);
    // elsewhere work is just one more topic.
    if (categoryId === "icebreakers" && workplace.test(text)) tags = new Set<Audience>(["team"]);
    else add("team");
  } else if (familyWords.test(text) && categoryId !== "party") {
    add("family");
  }

  // Truths, dares and "never have I ever" beyond the lightest level are for friends and couples.
  if (categoryId === "party" && depth >= 2) { tags.delete("team"); tags.delete("family"); }

  if (friendGroup.test(text)) tags = new Set<Audience>(["friends"]);
  else if (groupWords.test(text)) tags.delete("couple");

  if (tags.size === 0) tags.add("friends");
  return ALL_AUDIENCES.filter((a) => tags.has(a));
}

const cache = new Map<string, readonly Audience[]>();

/** Which groups a library question suits. Questions from packs and the player's own suit everyone. */
export function audiencesOf(q: Question): readonly Audience[] {
  if (q.kind === "trivia" || q.categoryId === "mine" || q.categoryId === "pack") return ALL_AUDIENCES;
  let tags = cache.get(q.id);
  if (!tags) {
    tags = audiencesOfEntry(q.categoryId, q.depth, (q as OpenQuestion).text);
    cache.set(q.id, tags);
  }
  return tags;
}

/** "everyone" (or an unknown choice) keeps every question. */
export function matchesAudience(q: Question, choice: string): boolean {
  return !isAudience(choice) || audiencesOf(q).includes(choice);
}

/** How many library questions suit each group, for the picker. */
export const audienceCounts: Record<Audience, number> = Object.fromEntries(
  ALL_AUDIENCES.map((a) => [a, questions.filter((q) => audiencesOf(q).includes(a)).length]),
) as Record<Audience, number>;

export const isAudienceChoice = (value: unknown): value is AudienceChoice => value === "everyone" || isAudience(value);

/** Who is playing, remembered between visits. "everyone" shows every question. */
export const audienceSetting = createSetting<AudienceChoice>("closer.audience", "everyone", isAudienceChoice);
