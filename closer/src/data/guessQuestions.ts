import type { GuessQuestion, GuessThemeId } from "../types";

// Guess My Answer: questions about taste and choices, each with four answers to pick from, so a guess
// can be marked right or wrong without trying to grade free text. Written to be answered about yourself.
type Entry = readonly [text: string, options: readonly [string, string, string, string]];

const sets: Record<GuessThemeId, Entry[]> = {
  love: [
    ["What's your ideal date night?", ["A cozy dinner at home", "A live concert", "A spontaneous road trip", "A cooking class together"]],
    ["How do you most like to hear 'I love you'?", ["In words", "With time together", "With a small gift", "With a helping hand"]],
    ["What does a perfect Sunday morning look like?", ["Breakfast in bed", "A long walk", "Sleeping in", "The farmers market"]],
    ["Which surprise would melt your heart?", ["A handwritten letter", "A weekend getaway", "Your favorite meal cooked for you", "Tickets to something fun"]],
    ["What matters most in a partner?", ["Humor", "Kindness", "Ambition", "Honesty"]],
    ["What do you do first after an argument?", ["Talk it out right away", "Take some space", "Write down your thoughts", "Make a peace offering"]],
    ["Which couple tradition would you pick?", ["Weekly game night", "An annual trip", "A new restaurant every month", "A daily walk"]],
    ["Where would you take a partner on vacation?", ["A beach", "A big city", "A mountain cabin", "A cultural tour"]],
    ["Which music sets the mood?", ["Slow jams", "Classic rock", "Pop hits", "Acoustic songs"]],
    ["How would you celebrate an anniversary?", ["A quiet dinner", "A big party", "A trip somewhere new", "An exchange of gifts"]],
  ],
  party: [
    ["What's your karaoke strategy?", ["A power ballad", "A duet", "Something funny", "Stay in the audience"]],
    ["At a party, where are you most likely to be?", ["On the dance floor", "Deep in conversation", "Running the music", "Helping in the kitchen"]],
    ["Which party game would you pick?", ["Charades", "Trivia", "Card games", "Truth or dare"]],
    ["Which snack wins every party?", ["Chips and dip", "Pizza", "Candy", "A cheese board"]],
    ["When do you usually arrive at a party?", ["Right on time", "Fashionably late", "First to arrive", "I leave early"]],
    ["Which costume would you wear?", ["A superhero", "A classic movie character", "A funny pun", "A group costume"]],
    ["Which party theme would you choose?", ["Retro 80s", "Masquerade", "Tropical", "Game night"]],
    ["How does your perfect party end?", ["Late-night pizza", "A dance-off", "Deep conversations", "Sleeping on the couch"]],
    ["What's on your party playlist?", ["Throwbacks", "Current hits", "Dance classics", "Chill vibes"]],
    ["What's your role in the party-planning group chat?", ["The organizer", "The idea person", "The comic relief", "The quiet supporter"]],
  ],
  "would-you-rather": [
    ["Which superpower would you pick?", ["Flying", "Invisibility", "Time travel", "Mind reading"]],
    ["Which job perk would you choose?", ["Unlimited vacation", "Free meals", "Remote work", "A big bonus"]],
    ["Where would you live forever?", ["A tropical beach", "Snowy mountains", "A big city", "The quiet countryside"]],
    ["Who would you have dinner with?", ["A historical figure", "Your favorite artist", "A famous chef", "A beloved relative"]],
    ["What would you give up forever?", ["Social media", "Sweets", "Coffee", "Streaming"]],
    ["Which pet would you pick?", ["A dog", "A cat", "A dragon", "A parrot"]],
    ["Which era would you live in?", ["Ancient Rome", "The Roaring Twenties", "The 1980s", "The far future"]],
    ["What's your ideal morning?", ["An early start", "A slow start", "The gym first", "Coffee and quiet"]],
    ["What would you do with a lottery win?", ["Travel the world", "Buy a dream home", "Give to charity", "Invest it"]],
    ["Which gadget would you want most?", ["A teleporter", "An instant translator", "A time-pause button", "A perfect memory"]],
  ],
  family: [
    ["Which holiday is your favorite?", ["A big winter holiday", "A summer holiday", "Your birthday", "Any holiday with great food"]],
    ["What's your favorite family dinner?", ["Pasta night", "A barbecue", "Soup and bread", "Takeout night"]],
    ["What did your family do for vacations?", ["The beach", "Camping", "Visiting relatives", "Road trips"]],
    ["As a kid, which were you?", ["The helper", "The rebel", "The comedian", "The quiet one"]],
    ["What was your favorite childhood game?", ["Hide and seek", "Board games", "Video games", "Make-believe"]],
    ["Who do you call first with good news?", ["Your mom", "Your dad", "A sibling", "A friend"]],
    ["Which family tradition would you keep?", ["Sunday dinners", "Holiday cookies", "Game night", "Family photos"]],
    ["Which smell reminds you of home?", ["Baking", "Fresh laundry", "Coffee", "Fresh-cut grass"]],
    ["What did you want to be when you grew up?", ["A doctor", "An artist", "An athlete", "An explorer"]],
    ["What's the best family movie night pick?", ["An animated classic", "A comedy", "An adventure", "A musical"]],
  ],
  icebreakers: [
    ["What do you drink in the morning?", ["Coffee", "Tea", "Juice", "Water"]],
    ["Which skill would you master?", ["Playing an instrument", "Speaking a new language", "Cooking like a chef", "Public speaking"]],
    ["What's your ideal place to work?", ["A quiet office", "A busy café", "Home", "Outdoors"]],
    ["How do you spend a weekend?", ["Adventure outdoors", "Relaxing at home", "Time with friends", "Catching up on chores"]],
    ["What's your go-to lunch?", ["A salad", "A sandwich", "Leftovers", "Takeout"]],
    ["What's your favorite season?", ["Spring", "Summer", "Autumn", "Winter"]],
    ["How do you like to start a meeting?", ["Quick small talk", "Straight to business", "A fun question", "Coffee and quiet"]],
    ["Which team activity would you pick?", ["An escape room", "A cooking class", "Volunteering", "Outdoor games"]],
    ["Which app do you open first?", ["Messages", "Email", "Music", "News"]],
    ["What do you do with a free hour?", ["Take a walk", "Read", "Nap", "Call a friend"]],
  ],
  imagination: [
    ["Which world would you explore?", ["An underwater city", "A space station", "An enchanted forest", "A futuristic metropolis"]],
    ["Which invention would you pick?", ["A pet translator", "A teleporter", "A mood-matching lamp", "A dream recorder"]],
    ["Which creature would you ride?", ["A dragon", "A giant eagle", "A dolphin", "A winged horse"]],
    ["Which room would you add to your house?", ["A library with a slide", "An indoor garden", "A movie theater", "A treehouse bedroom"]],
    ["Which magical ability would you want for a day?", ["Controlling the weather", "Talking to plants", "Shape-shifting", "Stopping time"]],
    ["Which snack would you try from another planet?", ["Glowing popcorn", "Floating fruit", "Rainbow soup", "Crunchy stardust"]],
    ["What would you name a brand-new color?", ["Midnight mango", "Stormy lilac", "Sunrise coral", "Forest echo"]],
    ["Which talent would you borrow for a day?", ["Master painter", "Famous singer", "Olympic athlete", "Genius inventor"]],
    ["Where would you hide a treasure?", ["A deep cave", "An old tree", "A floating island", "A hidden attic"]],
    ["Which genre best fits your life story?", ["Comedy", "Adventure", "Mystery", "Fantasy"]],
  ],
};

export const guessThemes: { id: GuessThemeId; name: string; description: string }[] = [
  { id: "love", name: "Love & Relationships", description: "Dates, love languages and what makes a partner." },
  { id: "party", name: "Party & Games", description: "Karaoke, snacks and party personalities." },
  { id: "would-you-rather", name: "Would You Rather & Dilemmas", description: "Superpowers, trade-offs and dream choices." },
  { id: "family", name: "Family & Memories", description: "Holidays, childhood and family traditions." },
  { id: "icebreakers", name: "Icebreakers & Team Building", description: "Easy picks for new friends and teams." },
  { id: "imagination", name: "Imagination & Creativity", description: "Invent, dream and explore imaginary worlds." },
];

export const guessQuestions: GuessQuestion[] = (Object.keys(sets) as GuessThemeId[]).flatMap((themeId) =>
  sets[themeId].map(([text, options], i) => ({ id: `guess-${themeId}-${i + 1}`, themeId, text, options })),
);

export const isGuessTheme = (value: string): value is GuessThemeId => guessThemes.some((t) => t.id === value);

/** The questions for a theme, or all of them for "mix" (or a category with no set of its own). */
export const guessPool = (themeId: string): GuessQuestion[] =>
  isGuessTheme(themeId) ? guessQuestions.filter((q) => q.themeId === themeId) : guessQuestions;
