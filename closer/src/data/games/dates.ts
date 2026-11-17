import { moreDateIdeas } from "./datesMore";
import { mergeUnique } from "./merge";

// Content for Date Night Roulette: ideas tagged by budget and mood. Works for couples and for any pair.

export type Budget = "free" | "low" | "treat";
export type Mood = "cozy" | "adventurous" | "romantic" | "silly";

export interface DateIdea {
  text: string;
  budget: Budget;
  mood: Mood;
}

export const budgetLabels: Record<Budget, string> = { free: "Free", low: "A little", treat: "A treat" };
export const moodLabels: Record<Mood, string> = { cozy: "Cozy", adventurous: "Adventurous", romantic: "Romantic", silly: "Silly" };
export const budgets = Object.keys(budgetLabels) as Budget[];
export const moods = Object.keys(moodLabels) as Mood[];

const baseDateIdeas: readonly DateIdea[] = [
  // Cozy
  { text: "Build a blanket fort and watch a movie inside it.", budget: "free", mood: "cozy" },
  { text: "Cook a recipe neither of you has tried, with the music on.", budget: "low", mood: "cozy" },
  { text: "Make hot chocolate and read to each other from a favorite book.", budget: "low", mood: "cozy" },
  { text: "Have a movie marathon of one actor's best films, with snacks.", budget: "low", mood: "cozy" },
  { text: "Take turns giving each other a ten-minute shoulder massage.", budget: "free", mood: "cozy" },
  { text: "Do a puzzle together with a playlist of your favorite songs.", budget: "low", mood: "cozy" },
  { text: "Order a favorite takeout and eat it on the living-room floor like a picnic.", budget: "treat", mood: "cozy" },
  { text: "Look through old photos and tell the story behind each one.", budget: "free", mood: "cozy" },
  { text: "Bake something together and take it to a neighbor.", budget: "low", mood: "cozy" },
  { text: "Have a tea or coffee tasting with three different kinds.", budget: "low", mood: "cozy" },
  { text: "Spend an evening on the sofa talking about your best day this year.", budget: "free", mood: "cozy" },
  { text: "Book a long bath or spa evening at home, with candles.", budget: "low", mood: "cozy" },
  // Adventurous
  { text: "Pick a trail you have never walked and bring a flask and snacks.", budget: "free", mood: "adventurous" },
  { text: "Take a bus or train to a town you have never visited, and wander.", budget: "low", mood: "adventurous" },
  { text: "Try a new sport together: bowling, climbing, mini golf or skating.", budget: "treat", mood: "adventurous" },
  { text: "Go stargazing somewhere far from city lights.", budget: "free", mood: "adventurous" },
  { text: "Rent bikes and ride somewhere you haven't been.", budget: "low", mood: "adventurous" },
  { text: "Visit a market and cook dinner from whatever looks best.", budget: "low", mood: "adventurous" },
  { text: "Go to a place you pass all the time and have never been inside.", budget: "free", mood: "adventurous" },
  { text: "Take a class together: pottery, dance or cooking.", budget: "treat", mood: "adventurous" },
  { text: "Watch the sunrise or sunset from a spot with a view.", budget: "free", mood: "adventurous" },
  { text: "Plan a day trip with no plan: take every second turn.", budget: "low", mood: "adventurous" },
  { text: "Go on a photo scavenger hunt around town.", budget: "free", mood: "adventurous" },
  { text: "Try a food you have never eaten at a restaurant you have never visited.", budget: "treat", mood: "adventurous" },
  // Romantic
  { text: "Cook a fancy dinner at home with candles, music and no phones.", budget: "low", mood: "romantic" },
  { text: "Write each other a short letter and read them aloud.", budget: "free", mood: "romantic" },
  { text: "Recreate your first date as closely as you can.", budget: "low", mood: "romantic" },
  { text: "Dance together in the kitchen to three songs that mean something to you.", budget: "free", mood: "romantic" },
  { text: "Have a candlelit picnic, indoors or out.", budget: "low", mood: "romantic" },
  { text: "Go out for a really nice dinner and dress up for it.", budget: "treat", mood: "romantic" },
  { text: "Take a slow walk at night and tell each other what you're grateful for.", budget: "free", mood: "romantic" },
  { text: "Book a night in a hotel or cabin nearby, just to be somewhere else.", budget: "treat", mood: "romantic" },
  { text: "Make a playlist of your story together and listen to it start to finish.", budget: "free", mood: "romantic" },
  { text: "Share a dessert at a café and take turns saying what you love about each other.", budget: "low", mood: "romantic" },
  { text: "Go for a sunset drive with your favorite songs and a snack.", budget: "low", mood: "romantic" },
  { text: "Create a small scrapbook of your favorite moments so far.", budget: "low", mood: "romantic" },
  // Silly
  { text: "Have a kitchen cook-off: same ingredients, different dishes, and a made-up judge.", budget: "low", mood: "silly" },
  { text: "Have a living-room talent show with costumes from your wardrobe.", budget: "free", mood: "silly" },
  { text: "Play a board game with one rule: the loser has to do a dare.", budget: "free", mood: "silly" },
  { text: "Try to draw each other's portrait while blindfolded.", budget: "free", mood: "silly" },
  { text: "Have a karaoke night using only songs from your teenage years.", budget: "free", mood: "silly" },
  { text: "Build the tallest tower you can from things in your kitchen.", budget: "free", mood: "silly" },
  { text: "Go to a thrift shop, pick an outfit for each other, and take photos.", budget: "low", mood: "silly" },
  { text: "Have an indoor Olympics: make up five events and give out medals.", budget: "free", mood: "silly" },
  { text: "Order one mystery item for each other online for under ten dollars.", budget: "low", mood: "silly" },
  { text: "Bake the strangest cake you can think of, then taste it bravely.", budget: "low", mood: "silly" },
  { text: "Write a story together, one word at a time, and read it as a drama.", budget: "free", mood: "silly" },
  { text: "Go bowling or mini golf, and make up a handicap system.", budget: "treat", mood: "silly" },
];

export const dateIdeas: readonly DateIdea[] = mergeUnique((x) => x.text, baseDateIdeas, moreDateIdeas);
