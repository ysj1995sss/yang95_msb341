// A final top-up of cards, so every pool is at least three times its first size once repeats are taken out (see merge.ts).
import type { ChoicePrompt } from "./know";

const two = (text: string, a: string, b: string): ChoicePrompt => ({ text, options: [a, b] });
const four = (text: string, a: string, b: string, c: string, d: string): ChoicePrompt => ({ text, options: [a, b, c, d] });

export const padNeverHaveIEver: readonly string[] = [
  "Never have I ever walked into a glass door.", "Never have I ever missed a flight.", "Never have I ever forgotten a friend's birthday.",
  "Never have I ever eaten cereal for dinner.", "Never have I ever worn my shirt inside out all day.", "Never have I ever sung in the shower at full volume.",
  "Never have I ever fallen asleep during a movie at the cinema.", "Never have I ever lost my keys inside my own home.", "Never have I ever planted a vegetable and eaten it.",
  "Never have I ever built a sandcastle taller than me.", "Never have I ever waved at someone who was not waving at me.", "Never have I ever tried to speak a language I did not know.",
  "Never have I ever stayed in a hotel with a view of the sea.", "Never have I ever ridden on a ferry.", "Never have I ever made a wish on a shooting star.",
  "Never have I ever kept a diary.", "Never have I ever painted a wall.", "Never have I ever stayed in a tent during a storm.",
  "Never have I ever eaten a whole watermelon slice in one sitting.", "Never have I ever given a speech to a room full of people.",
];

export const padLastWordTopics: readonly string[] = [
  "Things in a garden", "Fruits that are red", "Famous painters", "Words that end in 'ing'", "Things in a living room",
  "Items in a pencil case", "Birds", "Insects", "Things you do at a beach", "Things that are round",
  "Things in a hospital", "Famous inventors", "Sports played with a ball", "Things at a birthday party", "Things in a museum",
  "Kinds of weather", "Things in a forest", "Types of soup", "Things with wheels", "Board games",
  "Things in a bakery", "Famous mountains", "Musical instruments", "Things in a car", "Zoo animals",
];

export const padRapidFire: readonly string[] = [
  "A fruit you could eat every day?", "A place you feel calm?", "A sound that annoys you?", "A season you like?", "A snack you crave?",
  "A kind of shoe you wear?", "A chore you avoid?", "A subject you liked at school?", "A color you wear a lot?", "A game you play?",
  "A holiday you love?", "A flower you like?", "A tool you can use?", "A drink you have in the morning?", "A trip you remember?",
  "A bird you like?", "A word you say too often?", "A number you like?", "A sport you could try?", "A hero you admire?",
];

export const padThisOrThat: readonly ChoicePrompt[] = [
  two("Tea or hot chocolate?", "Tea", "Hot chocolate"),
  two("Beach holiday or mountain trip?", "Beach", "Mountains"),
  two("Text or phone call?", "Text", "Phone call"),
  two("Salty popcorn or sweet popcorn?", "Salty", "Sweet"),
  two("Sofa or beanbag?", "Sofa", "Beanbag"),
  two("Spring or autumn?", "Spring", "Autumn"),
  two("Bath or shower?", "Bath", "Shower"),
  two("Dogs or cats?", "Dogs", "Cats"),
  two("Dinner party or quiet dinner for two?", "Dinner party", "Quiet dinner"),
  two("Handwritten letter or voice message?", "Letter", "Voice message"),
  two("Stairs or elevator?", "Stairs", "Elevator"),
  two("Cold pizza or warm pizza?", "Cold", "Warm"),
];

export const padMatchPrompts: readonly ChoicePrompt[] = [
  four("Pick a bread.", "Baguette", "Sourdough", "Sandwich loaf", "Flatbread"),
  four("Pick a cheese.", "Cheddar", "Brie", "Mozzarella", "Feta"),
  four("Pick a type of pasta.", "Spaghetti", "Penne", "Ravioli", "Lasagne"),
  four("Pick a weekend plan.", "Sleep in", "Go out", "See friends", "Do a project"),
  four("Pick a board game.", "Chess", "Monopoly", "Scrabble", "Cards"),
  four("Pick a type of music.", "Pop", "Rock", "Jazz", "Classical"),
  four("Pick a color.", "Blue", "Green", "Red", "Yellow"),
  four("Pick a farm animal.", "Cow", "Sheep", "Pig", "Chicken"),
  four("Pick a sandwich filling.", "Cheese", "Ham", "Egg", "Peanut butter"),
  four("Pick a time to exercise.", "Early morning", "Lunchtime", "Evening", "Never"),
  four("Pick a gift.", "Flowers", "Book", "Chocolate", "Plant"),
  four("Pick a holiday activity.", "Swimming", "Sightseeing", "Reading", "Hiking"),
  four("Pick a hot drink.", "Tea", "Coffee", "Hot chocolate", "Herbal tea"),
  four("Pick a winter treat.", "Soup", "Mince pie", "Roast chestnuts", "Hot cider"),
  four("Pick a hobby.", "Cooking", "Gaming", "Gardening", "Drawing"),
  four("Pick a way to travel.", "Train", "Car", "Plane", "Bike"),
  four("Pick a snack at the cinema.", "Popcorn", "Nachos", "Candy", "Nothing"),
  four("Pick a rainy-day plan.", "Movie", "Baking", "Nap", "Board game"),
  four("Pick a morning routine.", "Coffee first", "Exercise first", "Shower first", "Phone first"),
  four("Pick a green food.", "Peas", "Broccoli", "Avocado", "Cucumber"),
  four("Pick a picnic food.", "Sandwiches", "Fruit", "Crisps", "Cake"),
  four("Pick a bedtime.", "Before 10", "Around 11", "Around midnight", "Much later"),
  four("Pick a pizza size.", "Small", "Medium", "Large", "Share a giant one"),
];
