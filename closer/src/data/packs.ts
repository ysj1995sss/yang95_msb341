import type { OpenQuestion, Pack } from "../types";

// Seasonal packs: ten questions for one occasion each. A pack is "in season" for the stretch of the
// year it belongs to (the app lists those first); the birthday pack is for any day. Question ids are
// the pack and its place in the list ("pack-valentines-3").
export const packs: Pack[] = [
  {
    id: "valentines",
    name: "Valentine's Day",
    blurb: "Date-night questions about the little things that make love feel like love.",
    icon: "Heart",
    gradient: "from-coral-500 to-plum-500",
    season: { from: [2, 1], to: [2, 20] },
    entries: [
      [1, "What's the most romantic thing you've seen in a movie that you'd actually want in real life?"],
      [1, "If we had a perfect Valentine's Day with no budget, how would it go?"],
      [1, "What's the sweetest thing you remember from our first few dates?"],
      [1, "Which love song would you dedicate to me?"],
      [2, "What's a small thing I do that makes you feel loved?"],
      [2, "Do you like to celebrate love with big gestures or quiet moments?"],
      [2, "What's a memory of us that you replay when we're apart?"],
      [3, "What do you hope we're still doing together in ten years?"],
      [3, "When did you first realize you were falling for me?"],
      [4, "What's something about our love that you've never found the words for?"],
    ],
  },
  {
    id: "new-year",
    name: "New Year Reset",
    blurb: "Look back, look ahead, and decide what you want more of.",
    icon: "Sparkles",
    gradient: "from-plum-500 to-sky-400",
    season: { from: [12, 26], to: [1, 15] },
    entries: [
      [1, "What's one tiny thing you want to do more of this year?"],
      [1, "What was the best thing you ate, watched or listened to this past year?"],
      [1, "If this year had a theme song, what would it be?"],
      [2, "What's a moment from last year you'd happily live again?"],
      [2, "What's one habit you want to leave behind, and what could replace it?"],
      [2, "What's a goal for this year that scares you a little?"],
      [2, "Who do you want to spend more time with this year?"],
      [3, "What did last year teach you that you don't want to forget?"],
      [3, "What would make this year feel like a success, even if nothing else goes right?"],
      [4, "What do you need to forgive yourself for before the year gets going?"],
    ],
  },
  {
    id: "summer",
    name: "Summer & Road Trips",
    blurb: "Long days, open windows and the stories that come with them.",
    icon: "Sun",
    gradient: "from-amber-400 to-coral-500",
    season: { from: [6, 1], to: [8, 31] },
    entries: [
      [1, "What's the perfect road trip snack and the perfect road trip song?"],
      [1, "Beach, lake or pool: where's your ideal summer day?"],
      [1, "What's the best ice cream flavor for a hot day, and why?"],
      [1, "If we could take a trip next weekend, where would we go?"],
      [2, "What's your favorite summer memory from when you were a kid?"],
      [2, "What's a place you'd drive for hours just to see the sunset?"],
      [2, "What's the most spontaneous summer adventure you've ever had?"],
      [2, "What summer tradition would you like to start with the people here?"],
      [3, "What's a summer that changed you, and how?"],
      [3, "What would you do this summer if you knew you couldn't fail?"],
    ],
  },
  {
    id: "spooky",
    name: "Spooky Season",
    blurb: "Costumes, candy and ghost stories for a cozy October night.",
    icon: "Ghost",
    gradient: "from-plum-700 to-coral-400",
    season: { from: [10, 1], to: [10, 31] },
    entries: [
      [1, "What's the best Halloween costume you've ever worn, or seen?"],
      [1, "Which movie monster would make the best roommate?"],
      [1, "What's your favorite Halloween candy, and which one is the worst?"],
      [1, "If you could haunt one place, where would it be?"],
      [2, "What's the spookiest thing that has ever happened to you?"],
      [2, "What's a childhood fear that makes you smile now?"],
      [2, "Would you spend a night in a haunted house? What would you bring?"],
      [2, "What's a ghost story, true or not, that you still remember?"],
      [3, "What scares you more as an adult than it did as a kid?"],
      [3, "If you could ask a ghost one question, what would it be?"],
    ],
  },
  {
    id: "gratitude",
    name: "Gratitude Table",
    blurb: "Pass the questions around the table this November.",
    icon: "Leaf",
    gradient: "from-amber-400 to-plum-500",
    season: { from: [11, 1], to: [11, 30] },
    entries: [
      [1, "What's one food you're always thankful to see on the table?"],
      [1, "What's something small that made you smile today?"],
      [1, "What's a gift you received that you still use or treasure?"],
      [2, "Who's someone you're thankful for, and what would you tell them?"],
      [2, "What's a challenge you're grateful for now that it's behind you?"],
      [2, "Which tradition at this time of year means the most to you?"],
      [2, "What's something about the people at this table that you're thankful for?"],
      [3, "What did you take for granted until it was gone?"],
      [3, "What's a hard moment that taught you to be thankful?"],
      [4, "Who have you never properly thanked, and what stopped you?"],
    ],
  },
  {
    id: "winter-holidays",
    name: "Winter Holidays",
    blurb: "Traditions, gifts and the people you wish were there.",
    icon: "Snowflake",
    gradient: "from-sky-400 to-plum-600",
    season: { from: [12, 1], to: [12, 31] },
    entries: [
      [1, "What's the best gift you ever gave?"],
      [1, "What's your favorite holiday song, and which one have you heard enough?"],
      [1, "What's the most memorable holiday meal you've had?"],
      [1, "Cozy night in or a big gathering: how do you like to celebrate?"],
      [2, "What holiday tradition would you never give up?"],
      [2, "What's a holiday memory that makes you smile?"],
      [2, "What's a tradition you'd like to start?"],
      [2, "What's the most meaningful gift you've ever received, and why?"],
      [3, "How do the holidays feel now compared with when you were a kid?"],
      [3, "Who do you miss most at this time of year, and what would you tell them?"],
    ],
  },
  {
    id: "birthday",
    name: "Birthday Celebration",
    blurb: "For any birthday, any day of the year.",
    icon: "Cake",
    gradient: "from-coral-400 to-amber-400",
    entries: [
      [1, "What's your favorite birthday memory?"],
      [1, "If you could plan the perfect birthday with no limits, what would happen?"],
      [1, "What's the best birthday gift you've ever received?"],
      [1, "Which age did you most look forward to turning, and why?"],
      [2, "What do you know now that you wish you'd known at your last birthday?"],
      [2, "What's a birthday tradition you'd like to keep or start?"],
      [2, "What do you want to do before your next birthday?"],
      [2, "What compliment would you most want to hear on your birthday?"],
      [3, "What would you tell your younger self on their birthday?"],
      [3, "What do you hope the next year of your life looks like?"],
    ],
  },
];

export const packById = (id: string): Pack | undefined => packs.find((p) => p.id === id);

export const packQuestions = (pack: Pack): OpenQuestion[] =>
  pack.entries.map(([depth, text], i) => ({ id: `pack-${pack.id}-${i + 1}`, categoryId: "pack", kind: "open", depth, text }));

const dayOfYear = (month: number, day: number) => month * 100 + day;

/** Whether `date` falls inside the pack's season (the local date). Any-day packs are never "in season". */
export function inSeason(pack: Pack, date: Date): boolean {
  if (!pack.season) return false;
  const today = dayOfYear(date.getMonth() + 1, date.getDate());
  const from = dayOfYear(...pack.season.from);
  const to = dayOfYear(...pack.season.to);
  return from <= to ? today >= from && today <= to : today >= from || today <= to;
}

/** Packs in season first, then the rest in their usual order. */
export function orderedPacks(date: Date): Pack[] {
  return [...packs.filter((p) => inSeason(p, date)), ...packs.filter((p) => !inSeason(p, date))];
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "Feb 1 to Feb 20", or "Any day" for a pack with no season. */
export function seasonLabel(pack: Pack): string {
  if (!pack.season) return "Any day";
  const [fm, fd] = pack.season.from;
  const [tm, td] = pack.season.to;
  return `${MONTHS[fm - 1]} ${fd} to ${MONTHS[tm - 1]} ${td}`;
}
