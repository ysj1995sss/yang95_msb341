import type { DailyQuestion } from "../types";

// One per day, in this order, starting again after the last one (utils/daily.ts).
const texts = [
  "What made you smile today?",
  "What's one thing you're looking forward to this week?",
  "Who is someone you're grateful for right now, and why?",
  "What's a small habit that makes your days better?",
  "If today had a theme song, what would it be?",
  "What's something new you learned recently?",
  "What would make tomorrow a great day?",
  "What's a compliment you received that you still remember?",
  "What's one thing you'd tell yourself a year ago?",
  "Where is your happy place?",
  "What's a simple pleasure you never get tired of?",
  "What's a goal you're quietly working toward?",
  "Who would you love to catch up with this week?",
  "What's the best thing you've eaten lately?",
  "What made you feel proud lately?",
  "What's a question you've been thinking about lately?",
  "What's one thing you'd like to let go of?",
  "What does a perfect evening look like for you?",
  "What's a book, show or podcast you'd recommend right now?",
  "What's something kind you could do for someone today?",
  "What's a fear you've overcome?",
  "When do you feel most like yourself?",
  "What's a tradition you'd like to start?",
  "What's the most beautiful place you've ever seen?",
  "What's a skill you're proud of building?",
  "What would you do with an extra free hour today?",
  "What's one word for your week so far, and why?",
  "Who taught you something important without realizing it?",
  "What's a dream you haven't told many people about?",
  "What's your favorite way to show someone you care?",
  "What's something you're excited to try this year?",
];

export const dailyQuestions: DailyQuestion[] = texts.map((text, i) => ({ id: `daily-${i + 1}`, text }));
