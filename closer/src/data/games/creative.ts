import { moreStoryStarters, moreCaptionScenes, moreProductProblems, moreProductTwists } from "./creativeMore";
import { mergeUnique } from "./merge";

// Content for the creative games: Story Chain, Caption This and Invent a Product.

/** Story Chain: the first line. Everyone adds the next one. */
const baseStoryStarters: readonly string[] = [
  "It was the morning the town woke up and every clock was running backwards.",
  "Nobody believed the lighthouse keeper when she said the lighthouse was humming a tune.",
  "The package arrived at midnight, and it was addressed to someone who did not exist yet.",
  "On the last day of summer, a small door appeared in the old oak tree.",
  "The robot waiter had one rule: never tell a customer the soup was cold.",
  "Deep under the library, something began to turn the pages by itself.",
  "The map led to a treasure, but the X was drawn right on top of the person holding it.",
  "Every night at nine, the neighbor's cat left the house with a tiny backpack.",
  "When the circus came to town, the lion asked the mayor for a favor.",
  "A single sock fell from the sky, and it was warm.",
  "The new student could speak to every animal, and today the animals were furious.",
  "At exactly noon, every phone in the city rang at once.",
  "The recipe called for one pinch of moonlight.",
  "The smallest dragon in the world had a very big problem.",
  "A bus with no driver pulled up, and the door opened just for us.",
  "The museum's most famous painting had changed overnight.",
  "A cloud landed in the backyard and refused to leave.",
  "The inventor pressed the big red button, and the whole house floated.",
  "The last pizza on Earth was sitting on the table.",
  "In the middle of the forest stood a bus stop, and a timetable that listed only tomorrow.",
  "The twins found a bottle on the beach with a note that began: 'Do not read this aloud.'",
  "Every time the baker sneezed, something strange appeared in the shop window.",
  "The ghost wasn't scary. He just wanted help with his taxes.",
  "Someone had been leaving tiny shoes outside the front door every morning.",
  "The elevator in the old hotel had a button for a floor that wasn't there.",
  "On Tuesday, gravity took the day off.",
  "The wizard had lost his wand, and it had been found by a very confused goat.",
  "Our spaceship's snack machine had started giving advice.",
  "The pirates were tough, but they had one big fear: being on time.",
  "When the moon came down to visit, it asked for a cup of tea.",
];

/** Caption This: a made-up scene to write a funny caption for. */
export interface Scene {
  emoji: string;
  setup: string;
}

const baseCaptionScenes: readonly Scene[] = [
  { emoji: "🐶🎩🚲", setup: "A dog in a top hat is riding a bicycle past a very surprised crowd." },
  { emoji: "🐱🍕🌙", setup: "A cat is sitting on the roof at midnight, eating a whole pizza." },
  { emoji: "🦆🏊‍♂️🕶️", setup: "A duck with sunglasses is leading a swimming class." },
  { emoji: "🧑‍🍳🔥😳", setup: "A chef holds a flaming pan and stares at the camera." },
  { emoji: "🐢🏁🏆", setup: "A tortoise has just crossed the finish line, and everyone is cheering." },
  { emoji: "🦒🛋️📺", setup: "A giraffe is squeezed onto a tiny sofa, watching TV." },
  { emoji: "🐧☕📰", setup: "A penguin is reading the newspaper in a café, looking worried." },
  { emoji: "🐘🪑🎻", setup: "An elephant has been given a violin and a very small chair." },
  { emoji: "🚀🐑🌌", setup: "A sheep in a space suit floats past a space station." },
  { emoji: "🐙👔💻", setup: "An octopus in a tie is typing eight emails at once." },
  { emoji: "🦆🛒🎈", setup: "A duck is pushing a shopping cart full of balloons." },
  { emoji: "🐻🛁🫧", setup: "A bear is enjoying a bubble bath and does not want to be disturbed." },
  { emoji: "🧑‍🚀🌮🪐", setup: "An astronaut has found a taco on a faraway planet." },
  { emoji: "🐓⏰😴", setup: "A rooster has overslept, and the sun is already high." },
  { emoji: "🐸🎤🎶", setup: "A frog is on stage in front of a huge audience, taking the song very seriously." },
  { emoji: "🦄🚕🌧️", setup: "A unicorn is trying to hail a taxi in the rain." },
  { emoji: "🐼🧗⛰️", setup: "A panda is halfway up a mountain, holding a snack." },
  { emoji: "🐶📦😬", setup: "A dog sits calmly in the middle of a very empty cardboard box that was full a moment ago." },
  { emoji: "🧙‍♂️📶😡", setup: "A wizard is holding his wand up high, trying to get a signal." },
  { emoji: "🐈🧶🌀", setup: "A cat is tangled in yarn and looks very proud." },
  { emoji: "🦖🛹🌴", setup: "A dinosaur is learning to skateboard, with one very small helmet." },
  { emoji: "🐿️🌰🏦", setup: "A squirrel is hiding nuts in a bank vault." },
  { emoji: "🐝🍯👑", setup: "A bee in a crown is giving orders to a very long line of other bees." },
  { emoji: "🐠🔭🪟", setup: "A goldfish is looking through a telescope at the living room." },
  { emoji: "🐰🎒📚", setup: "A rabbit is running late for school with a backpack taller than they are." },
  { emoji: "🦉🧑‍⚖️⚖️", setup: "An owl in a wig is the judge in a very serious court of cookies." },
  { emoji: "🐳🚿🎵", setup: "A whale has moved into a bathtub, and has opinions about the soap." },
  { emoji: "🐊🪥😁", setup: "A crocodile is brushing his teeth, and the dentist is brave." },
  { emoji: "🦔🎈🏙️", setup: "A hedgehog holding a balloon is floating over the city, calm as can be." },
  { emoji: "🐑💈✂️", setup: "A sheep is at the barber, asking for 'just a little off the top'." },
];

/** Invent a Product: a problem to solve… */
const baseProductProblems: readonly string[] = [
  "People keep losing their keys.", "Umbrellas never work in the wind.", "Mornings are too hard.",
  "Leftovers always get forgotten in the fridge.", "Nobody can find a matching sock.", "Phone batteries never last long enough.",
  "Waiting in line is boring.", "Houseplants keep dying.", "Packing for a trip takes forever.",
  "Dogs hate bath time.", "Traffic jams are tiring.", "Cold coffee is a tragedy.",
  "Charging cables are always tangled.", "Elevators are awkward.", "Kids won't eat vegetables.",
  "Rain ruins every picnic.", "Birthday parties need new ideas.", "Pillows go flat.",
  "Alarm clocks are too gentle.", "Cats knock things off tables.", "Remote controls vanish into sofas.",
  "People forget birthdays.", "Shoes get smelly.", "Moving house is a nightmare.",
  "Homework is dull.", "Sunscreen is greasy.", "Long flights are too long.",
  "Meetings go on forever.", "Lunch boxes get squashed.", "Nobody likes washing up.",
  "Fog makes everyone late.", "Sandwiches fall apart.", "Libraries are too quiet for kids.",
  "Hiccups won't go away.", "Bicycles get stolen.", "Beaches are too hot.",
  "People talk too loudly on trains.", "Cooking for one is wasteful.", "Snow is hard to shovel.",
  "Camping tents are hard to put up.",
];

/** …and a twist the invention has to include. */
const baseProductTwists: readonly string[] = [
  "It must be shaped like a banana.", "It has to be powered by a hamster.", "It only works on Wednesdays.",
  "It must sing when used.", "It has to fit in a pocket.", "It is sold only to grandparents.",
  "It must be completely silent.", "It has to be waterproof.", "It can only be bought with coins.",
  "It must have a catchy slogan.", "It comes in exactly three colors.", "It has to be edible.",
  "It must work in space.", "It has to be a subscription.", "It must fold into the size of a card.",
  "It talks, but only in rhymes.", "It has a very serious name.", "It must be invented by a pirate.",
  "It has a secret second use.", "It has to be wearable.",
];

export const storyStarters: readonly string[] = mergeUnique((x) => x, baseStoryStarters, moreStoryStarters);
export const captionScenes: readonly Scene[] = mergeUnique((x) => JSON.stringify(x), baseCaptionScenes, moreCaptionScenes);
export const productProblems: readonly string[] = mergeUnique((x) => x, baseProductProblems, moreProductProblems);
export const productTwists: readonly string[] = mergeUnique((x) => x, baseProductTwists, moreProductTwists);
