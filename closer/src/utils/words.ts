const WORDS = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve"];

/** 7 becomes "Seven", for headings that count the experiences. Falls back to digits past twelve. */
export const numberWord = (n: number): string => WORDS[n] ?? String(n);
