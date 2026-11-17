// Content for Fact or Fiction, Higher or Lower and Guess the Price. These are well-known facts and
// rounded numbers; "about" is in the wording wherever a number is not exact.

import type { FactGroup } from "../../utils/games/higherLower";
import { moreClaims, moreFactGroups, morePriceItems } from "./brainMore";
import { mergeUnique } from "./merge";

export interface Claim {
  text: string;
  /** True when the claim is true. */
  isTrue: boolean;
  /** One line shown after the answer. */
  why: string;
}

const baseClaims: readonly Claim[] = [
  { text: "Octopuses have three hearts.", isTrue: true, why: "Two pump blood to the gills and one to the rest of the body." },
  { text: "The Great Wall of China can be seen from the Moon with the naked eye.", isTrue: false, why: "It is far too narrow to see from that distance." },
  { text: "Bananas are berries, but strawberries are not.", isTrue: true, why: "Botanically, a berry grows from one flower with one ovary and has seeds inside." },
  { text: "Humans only use 10% of their brains.", isTrue: false, why: "Scans show we use virtually all of the brain, just not all at once." },
  { text: "A day on Venus is longer than its year.", isTrue: true, why: "Venus spins very slowly: one turn takes about 243 Earth days, but its orbit takes about 225." },
  { text: "Goldfish have a three-second memory.", isTrue: false, why: "They can remember things for months." },
  { text: "Honey found in ancient Egyptian tombs was still safe to eat.", isTrue: true, why: "Honey is so low in water that it hardly spoils when sealed." },
  { text: "Bats are blind.", isTrue: false, why: "Bats can see, and many also use sound to find their way." },
  { text: "Wombat droppings are cube-shaped.", isTrue: true, why: "It helps the droppings stay put when wombats use them to mark territory." },
  { text: "Lightning never strikes the same place twice.", isTrue: false, why: "Tall buildings like the Empire State Building are struck many times a year." },
  { text: "The Eiffel Tower is taller in summer than in winter.", isTrue: true, why: "Metal expands in heat, adding roughly 15 centimeters." },
  { text: "Napoleon was unusually short.", isTrue: false, why: "He was about average height for his time; the myth came from a mix-up of units and cartoons." },
  { text: "Sharks are older than trees.", isTrue: true, why: "Sharks appeared hundreds of millions of years ago, before the first trees." },
  { text: "Different parts of the tongue taste different flavors.", isTrue: false, why: "Every taste can be sensed all over the tongue." },
  { text: "Sound travels faster through water than through air.", isTrue: true, why: "Roughly four times faster." },
  { text: "Chameleons change color mainly to hide.", isTrue: false, why: "It is mostly about mood, signals and temperature." },
  { text: "A group of flamingos is called a flamboyance.", isTrue: true, why: "A real and fabulous word." },
  { text: "Bulls charge because they hate the color red.", isTrue: false, why: "Bulls cannot see red; the moving cape is what they react to." },
  { text: "Cleopatra lived closer in time to the Moon landing than to the building of the Great Pyramid.", isTrue: true, why: "The Great Pyramid is about 2,500 years older than Cleopatra; the Moon landing is about 2,000 years after her." },
  { text: "Vikings wore horned helmets in battle.", isTrue: false, why: "There is no evidence for it; horned helmets came from 19th-century costume designs." },
  { text: "Lightning can be hotter than the surface of the Sun.", isTrue: true, why: "A bolt heats the air to about 30,000 degrees Celsius." },
  { text: "Shaving makes hair grow back thicker.", isTrue: false, why: "It only feels that way because the hair has a blunt tip." },
  { text: "Tomatoes are fruits.", isTrue: true, why: "They are the seed-carrying part of the plant, so botanically they are fruits." },
  { text: "You swallow eight spiders a year while you sleep.", isTrue: false, why: "It's an old myth with no evidence." },
  { text: "Mauna Kea is taller than Mount Everest when measured from base to peak.", isTrue: true, why: "Most of Mauna Kea is under the sea, so measured from the ocean floor it is taller." },
  { text: "Fortune cookies were invented in China.", isTrue: false, why: "They grew up in California and are rare in China." },
  { text: "Antarctica is a desert.", isTrue: true, why: "A desert is defined by how little rain or snow falls, and Antarctica gets very little." },
  { text: "Peanuts are nuts.", isTrue: false, why: "They are legumes, related to beans and lentils." },
  { text: "Russia has eleven time zones.", isTrue: true, why: "It stretches across more than a quarter of the way around the globe." },
  { text: "Pineapples grow on trees.", isTrue: false, why: "They grow on a low plant, one fruit per plant." },
  { text: "The Pacific Ocean is larger than all of Earth's land put together.", isTrue: true, why: "It covers about 165 million square kilometers; the land is about 149 million." },
  { text: "Spiders are insects.", isTrue: false, why: "They have eight legs and are arachnids." },
  { text: "Sloths can hold their breath longer than dolphins.", isTrue: true, why: "A slow heartbeat lets sloths go without air for up to about 40 minutes." },
  { text: "Whales are a kind of fish.", isTrue: false, why: "They are mammals: they breathe air and nurse their young." },
  { text: "A year on Mercury is shorter than 100 Earth days.", isTrue: true, why: "Mercury orbits the Sun in about 88 days." },
  { text: "Penguins live at the North Pole.", isTrue: false, why: "Penguins live in the Southern Hemisphere, and polar bears at the north." },
  { text: "The Statue of Liberty was a gift from France.", isTrue: true, why: "It arrived in 1885 as a sign of friendship." },
  { text: "Mount Fuji is in China.", isTrue: false, why: "It is in Japan." },
  { text: "Light from the Sun takes about eight minutes to reach Earth.", isTrue: true, why: "The Sun is about 150 million kilometers away." },
  { text: "Starfish have a brain.", isTrue: false, why: "They have a network of nerves but no brain." },
  { text: "Dolphins sleep with half of their brain awake.", isTrue: true, why: "That way they can still surface to breathe." },
  { text: "Birds are descended from dinosaurs.", isTrue: true, why: "Birds are living members of the dinosaur family tree." },
  { text: "Alaska is the largest US state by area.", isTrue: true, why: "It is more than twice the size of Texas." },
  { text: "Australia is wider than the Moon.", isTrue: true, why: "Australia is about 4,000 km across; the Moon is about 3,500 km." },
  { text: "The shortest war in history lasted 38 minutes.", isTrue: true, why: "The Anglo-Zanzibar War of 1896 holds the record." },
  { text: "Oxford University is older than the Aztec Empire.", isTrue: true, why: "Teaching at Oxford began around 1096; the Aztec capital was founded in 1325." },
  { text: "Elephants are the only animals that can't jump.", isTrue: false, why: "Many animals can't jump, including sloths and hippos." },
  { text: "Water boils at a lower temperature on a high mountain.", isTrue: true, why: "There is less air pressure, so water boils at less than 100 degrees Celsius." },
  { text: "The blue whale is the largest animal that has ever lived.", isTrue: true, why: "It is even bigger than the largest dinosaurs known." },
  { text: "An ostrich buries its head in the sand when scared.", isTrue: false, why: "It's a myth; they run, or lie flat on the ground." },
  { text: "Cows have best friends.", isTrue: true, why: "Studies show cows form close bonds and get stressed when apart." },
];

/** Higher or Lower: numbers to compare within one group. */
const baseFactGroups: readonly FactGroup[] = [
  {
    id: "mountains", question: "How high is the mountain?", unit: "m", higher: "higher", lower: "lower",
    facts: [
      { name: "Mount Everest", value: 8849 }, { name: "K2", value: 8611 }, { name: "Kilimanjaro", value: 5895 },
      { name: "Mont Blanc", value: 4806 }, { name: "Denali", value: 6190 }, { name: "Mount Fuji", value: 3776 },
      { name: "Ben Nevis", value: 1345 }, { name: "The Matterhorn", value: 4478 }, { name: "Aconcagua", value: 6961 },
    ],
  },
  {
    id: "buildings", question: "How tall is the landmark?", unit: "m", higher: "taller", lower: "shorter",
    facts: [
      { name: "Burj Khalifa", value: 828 }, { name: "The Eiffel Tower", value: 330 }, { name: "The Empire State Building", value: 443 },
      { name: "The Statue of Liberty with its base", value: 93 }, { name: "Big Ben's tower", value: 96 }, { name: "The CN Tower", value: 553 },
      { name: "The Space Needle", value: 184 }, { name: "The Leaning Tower of Pisa", value: 56 }, { name: "Taipei 101", value: 508 },
    ],
  },
  {
    id: "planets", question: "How wide is it?", unit: "km", higher: "wider", lower: "narrower",
    facts: [
      { name: "Mercury", value: 4879 }, { name: "Venus", value: 12104 }, { name: "Earth", value: 12742 },
      { name: "Mars", value: 6779 }, { name: "Jupiter", value: 139820 }, { name: "Saturn", value: 116460 },
      { name: "Uranus", value: 50724 }, { name: "Neptune", value: 49244 }, { name: "The Moon", value: 3474 },
    ],
  },
  {
    id: "distance-sun", question: "How far from the Sun is it (in millions of kilometers)?", unit: "million km", higher: "farther", lower: "closer",
    facts: [
      { name: "Mercury", value: 58 }, { name: "Venus", value: 108 }, { name: "Earth", value: 150 },
      { name: "Mars", value: 228 }, { name: "Jupiter", value: 778 }, { name: "Saturn", value: 1434 },
      { name: "Uranus", value: 2871 }, { name: "Neptune", value: 4495 },
    ],
  },
  {
    id: "inventions", question: "When was it invented?", unit: "year", higher: "later", lower: "earlier",
    facts: [
      { name: "The telephone", value: 1876 }, { name: "The practical light bulb", value: 1879 }, { name: "The first powered airplane flight", value: 1903 },
      { name: "Penicillin", value: 1928 }, { name: "The World Wide Web", value: 1989 }, { name: "The first iPhone", value: 2007 },
      { name: "The printing press in Europe", value: 1440 }, { name: "The first email", value: 1971 }, { name: "The first public television broadcast in the US", value: 1928 },
    ],
  },
  {
    id: "animal-speed", question: "How fast can it go?", unit: "km/h", higher: "faster", lower: "slower",
    facts: [
      { name: "A cheetah", value: 110 }, { name: "A lion", value: 80 }, { name: "A greyhound", value: 72 },
      { name: "An ostrich", value: 70 }, { name: "A giraffe", value: 58 }, { name: "A sprinting human champion", value: 44 },
      { name: "An elephant", value: 40 }, { name: "A domestic cat", value: 48 },
    ],
  },
];

/** Guess the Price: roughly what it costs in the US. Four prices, one close to typical. */
export interface PriceItem {
  item: string;
  options: readonly string[];
  /** Index of the closest price. */
  answer: 0 | 1 | 2 | 3;
}

const basePriceItems: readonly PriceItem[] = [
  { item: "A can of soda from a shop", options: ["$1.50", "$4", "$8", "$15"], answer: 0 },
  { item: "A movie ticket", options: ["$3", "$6", "$13", "$40"], answer: 2 },
  { item: "A cup of coffee at a café", options: ["$1", "$4", "$9", "$15"], answer: 1 },
  { item: "A paperback novel", options: ["$4", "$15", "$40", "$75"], answer: 1 },
  { item: "A pair of jeans", options: ["$10", "$25", "$60", "$250"], answer: 2 },
  { item: "A new flagship smartphone", options: ["$300", "$600", "$900", "$2,500"], answer: 2 },
  { item: "A city bus ride", options: ["$0.25", "$2", "$7", "$15"], answer: 1 },
  { item: "A gallon of milk", options: ["$1", "$4", "$9", "$15"], answer: 1 },
  { item: "A large delivered pizza", options: ["$6", "$20", "$50", "$90"], answer: 1 },
  { item: "A night in a mid-range hotel", options: ["$30", "$80", "$150", "$600"], answer: 2 },
  { item: "An average new car", options: ["$18,000", "$28,000", "$48,000", "$98,000"], answer: 2 },
  { item: "Large popcorn at the cinema", options: ["$2", "$9", "$20", "$35"], answer: 1 },
  { item: "A toothbrush", options: ["$0.50", "$3", "$12", "$25"], answer: 1 },
  { item: "A basic adult bicycle", options: ["$60", "$400", "$1,500", "$4,000"], answer: 1 },
  { item: "A mid-range laptop", options: ["$150", "$700", "$2,500", "$5,000"], answer: 1 },
  { item: "A day ticket to a big theme park", options: ["$30", "$70", "$150", "$450"], answer: 2 },
  { item: "A pair of running shoes", options: ["$20", "$50", "$120", "$400"], answer: 2 },
  { item: "A tank of gas for a family car", options: ["$10", "$50", "$150", "$300"], answer: 1 },
  { item: "A cross-country economy flight", options: ["$60", "$350", "$1,500", "$4,000"], answer: 1 },
  { item: "A haircut", options: ["$8", "$30", "$100", "$250"], answer: 1 },
  { item: "A fast-food burger meal", options: ["$3", "$10", "$25", "$45"], answer: 1 },
  { item: "A first-class postage stamp", options: ["$0.07", "$0.75", "$7.50", "$75"], answer: 1 },
  { item: "A single scoop ice cream cone", options: ["$0.50", "$4", "$12", "$25"], answer: 1 },
  { item: "A college textbook", options: ["$30", "$120", "$600", "$1,500"], answer: 1 },
  { item: "A beginner acoustic guitar", options: ["$25", "$200", "$1,200", "$3,000"], answer: 1 },
];

export const claims: readonly Claim[] = mergeUnique((x) => x.text, baseClaims, moreClaims);
export const factGroups: readonly FactGroup[] = mergeUnique((x) => x.id, baseFactGroups, moreFactGroups);
export const priceItems: readonly PriceItem[] = mergeUnique((x) => x.item, basePriceItems, morePriceItems);
