import type { TriviaEntry } from "../../types";

// Trivia & Brain Battles (trivia-1, trivia-2, …). The first 12 keep the ids they had before.
// Difficulty: 1 Easy, 2 Medium, 3 Hard, 4 Expert. The facts were checked against reference sources
// (Britannica, Guinness World Records, Wikipedia, USGS and similar); see closer/README.md.
// The correct answer's position varies on purpose, so it can't be guessed from where it sits.
export const trivia: TriviaEntry[] = [
  {
    topic: "Geography", source: "Pacific Ocean", difficulty: 1,
    text: "What is the largest ocean on Earth?",
    options: ["Atlantic Ocean", "Indian Ocean", "Pacific Ocean", "Arctic Ocean"], answer: 2,
    explanation: "The Pacific covers about a third of Earth's surface, more than all the land combined.",
  },
  {
    topic: "Science", source: "Mars", difficulty: 1,
    text: "Which planet is known as the Red Planet?",
    options: ["Venus", "Mars", "Jupiter", "Mercury"], answer: 1,
    explanation: "Mars looks red because its surface is rich in iron oxide, the same compound as rust.",
  },
  {
    topic: "Art, books & culture", source: "Mona Lisa", difficulty: 1,
    text: "Who painted the Mona Lisa?",
    options: ["Michelangelo", "Raphael", "Leonardo da Vinci", "Vincent van Gogh"], answer: 2,
    explanation: "Leonardo da Vinci painted it in the early 1500s. It hangs in the Louvre in Paris.",
  },
  {
    topic: "Science", source: "Gold", difficulty: 2,
    text: "What is the chemical symbol for gold?",
    options: ["Ag", "Au", "Gd", "Go"], answer: 1,
    explanation: "Au comes from aurum, the Latin word for gold. Ag is silver.",
  },
  {
    topic: "History", source: "Apollo 11", difficulty: 2,
    text: "In what year did people first walk on the Moon?",
    options: ["1961", "1965", "1969", "1972"], answer: 2,
    explanation: "Neil Armstrong and Buzz Aldrin landed with Apollo 11 in July 1969.",
  },
  {
    topic: "Geography", source: "Canberra", difficulty: 2,
    text: "What is the capital of Australia?",
    options: ["Sydney", "Melbourne", "Canberra", "Perth"], answer: 2,
    explanation: "Canberra was chosen as a compromise between rivals Sydney and Melbourne.",
  },
  {
    topic: "Science", source: "Human skeleton", difficulty: 2,
    text: "How many bones are in the adult human body?",
    options: ["186", "206", "226", "256"], answer: 1,
    explanation: "Adults have 206 bones. Babies start with more, and some fuse together as they grow.",
  },
  {
    topic: "Movies & TV", source: "Titanic (1997 film)", difficulty: 3,
    text: "Which 1997 film was the first to earn more than $1 billion at the box office worldwide?",
    options: ["Titanic", "Jurassic Park", "The Lion King", "Independence Day"], answer: 0,
    explanation: "James Cameron's Titanic passed $1 billion worldwide in 1998, a first for any film.",
  },
  {
    topic: "Geography", source: "Amazon River", difficulty: 2,
    text: "What is the longest river in South America?",
    options: ["Paraná", "Orinoco", "Amazon", "Magdalena"], answer: 2,
    explanation: "The Amazon runs about 6,400 km and carries more water than any other river on Earth.",
  },
  {
    topic: "Science", source: "Photosynthesis", difficulty: 1,
    text: "Which gas do plants take in from the air to make their food?",
    options: ["Oxygen", "Nitrogen", "Carbon dioxide", "Hydrogen"], answer: 2,
    explanation: "Photosynthesis turns carbon dioxide and water into sugar, releasing oxygen.",
  },
  {
    topic: "General & logic", source: "Diamond", difficulty: 1,
    text: "What is the hardest natural substance?",
    options: ["Quartz", "Diamond", "Graphite", "Topaz"], answer: 1,
    explanation: "Diamond tops the Mohs hardness scale at 10. Graphite is also carbon, but very soft.",
  },
  {
    topic: "History", source: "Berlin Wall", difficulty: 2,
    text: "Which city's wall fell in 1989, opening the way to German reunification?",
    options: ["Vienna", "Berlin", "Prague", "Warsaw"], answer: 1,
    explanation: "The Berlin Wall fell on 9 November 1989, and Germany reunified in October 1990.",
  },

  // Easy
  {
    topic: "Geography", source: "Seine", difficulty: 1,
    text: "Which river flows through the city of Paris?",
    options: ["Loire", "Rhône", "Garonne", "Seine"], answer: 3,
    explanation: "The Seine winds through the heart of Paris on its way to the English Channel.",
  },
  {
    topic: "Geography", source: "Sahara", difficulty: 1,
    text: "Which is the largest hot desert in the world?",
    options: ["Sahara", "Gobi", "Kalahari", "Arabian"], answer: 0,
    explanation: "The Sahara spans much of northern Africa and is about as large as the United States. Antarctica is bigger overall, but it's a cold desert.",
  },
  {
    topic: "History", source: "World War II", difficulty: 1,
    text: "In what year did World War II end?",
    options: ["1941", "1943", "1944", "1945"], answer: 3,
    explanation: "Germany surrendered in May 1945, and Japan formally surrendered in September of that year.",
  },
  {
    topic: "History", source: "Machu Picchu", difficulty: 1,
    text: "Which ancient civilization built the mountain city of Machu Picchu in Peru?",
    options: ["Inca", "Aztec", "Maya", "Olmec"], answer: 0,
    explanation: "The Inca built Machu Picchu in the 15th century, high in the Andes.",
  },
  {
    topic: "Science", source: "Mitochondrion", difficulty: 1,
    text: "What is the powerhouse of the cell?",
    options: ["Mitochondria", "Nucleus", "Ribosome", "Golgi apparatus"], answer: 0,
    explanation: "Mitochondria turn nutrients into the energy a cell uses to do its work.",
  },
  {
    topic: "Music & entertainment", source: "Princess Peach", difficulty: 1,
    text: "Which princess does Mario usually rescue in the Super Mario games?",
    options: ["Zelda", "Daisy", "Rosalina", "Peach"], answer: 3,
    explanation: "Princess Peach is kidnapped by Bowser in most of the Mario games.",
  },
  {
    topic: "Art, books & culture", source: "Hedwig (Harry Potter)", difficulty: 1,
    text: "What is the name of Harry Potter's pet owl?",
    options: ["Errol", "Hedwig", "Pigwidgeon", "Fawkes"], answer: 1,
    explanation: "Hagrid gave Harry the snowy owl Hedwig for his eleventh birthday.",
  },
  {
    topic: "General & logic", source: "Power of two", difficulty: 1,
    text: "Which number completes the pattern 2, 4, 8, 16?",
    options: ["24", "30", "32", "36"], answer: 2,
    explanation: "Each number is double the one before it, so 16 × 2 = 32.",
  },

  // Medium
  {
    topic: "Geography", source: "Vatican City", difficulty: 2,
    text: "What is the smallest country in the world by area?",
    options: ["Monaco", "San Marino", "Liechtenstein", "Vatican City"], answer: 3,
    explanation: "Vatican City covers only about 0.44 square kilometers (0.17 square miles).",
  },
  {
    topic: "Geography", source: "Mount Kilimanjaro", difficulty: 2,
    text: "In which country is Mount Kilimanjaro, Africa's tallest mountain?",
    options: ["Tanzania", "Kenya", "Uganda", "Ethiopia"], answer: 0,
    explanation: "Kilimanjaro rises about 5,895 meters (19,341 feet) above sea level in northern Tanzania.",
  },
  {
    topic: "History", source: "Hadrian's Wall", difficulty: 2,
    text: "Which wall was built across northern England in the 2nd century to guard the edge of the Roman Empire?",
    options: ["The Great Wall", "Offa's Dyke", "Hadrian's Wall", "The Berlin Wall"], answer: 2,
    explanation: "Construction began around AD 122 under the Roman Emperor Hadrian.",
  },
  {
    topic: "Science", source: "Atmosphere of Earth", difficulty: 2,
    text: "Which gas makes up most of Earth's atmosphere?",
    options: ["Oxygen", "Nitrogen", "Carbon dioxide", "Argon"], answer: 1,
    explanation: "About 78% of the air is nitrogen. Oxygen makes up about 21%.",
  },
  {
    topic: "Art, books & culture", source: "Diwali", difficulty: 2,
    text: "Which festival is known as the Festival of Lights in India?",
    options: ["Holi", "Navratri", "Raksha Bandhan", "Diwali"], answer: 3,
    explanation: "Diwali celebrates the victory of light over darkness with lamps, lights, and sweets.",
  },
  {
    topic: "Science", source: "Komodo dragon", difficulty: 2,
    text: "What kind of animal is a Komodo dragon?",
    options: ["Lizard", "Snake", "Crocodile", "Turtle"], answer: 0,
    explanation: "The Komodo dragon is the largest living lizard.",
  },
  {
    topic: "General & logic", source: "Fibonacci sequence", difficulty: 2,
    text: "What is the next number in this sequence: 1, 1, 2, 3, 5, 8?",
    options: ["11", "12", "13", "15"], answer: 2,
    explanation: "Each number is the sum of the two before it (5 + 8 = 13). This is the Fibonacci sequence.",
  },

  // Hard
  {
    topic: "Geography", source: "Geography of Canada", difficulty: 3,
    text: "Which country has more lakes than any other?",
    options: ["Russia", "Finland", "United States", "Canada"], answer: 3,
    explanation: "Canada has more lakes than any other country. Estimates run up to about two million, depending on how small a lake can be.",
  },
  {
    topic: "History", source: "Magna Carta", difficulty: 3,
    text: "Which English king sealed the Magna Carta in 1215?",
    options: ["King John", "Richard I", "Henry II", "Edward I"], answer: 0,
    explanation: "King John agreed to the charter at Runnymede, limiting the power of the crown.",
  },
  {
    topic: "History", source: "Marie Curie", difficulty: 3,
    text: "Who was the first woman to win a Nobel Prize?",
    options: ["Mother Teresa", "Marie Curie", "Florence Nightingale", "Rosalind Franklin"], answer: 1,
    explanation: "Marie Curie won the Nobel Prize in Physics in 1903, and the Prize in Chemistry in 1911.",
  },
  {
    topic: "Science", source: "Speed of light", difficulty: 3,
    text: "About how fast does light travel in a vacuum?",
    options: ["About 300 km per second", "About 3,000 km per second", "About 30,000 km per second", "About 300,000 km per second"], answer: 3,
    explanation: "Light travels about 299,792 kilometers per second, which is nearly 300,000.",
  },
  {
    topic: "Science", source: "Moons of Saturn", difficulty: 3,
    text: "Which planet in our solar system has the most known moons?",
    options: ["Jupiter", "Saturn", "Uranus", "Neptune"], answer: 1,
    explanation: "Saturn has more known moons than any other planet, and astronomers keep finding new ones.",
  },
  {
    topic: "Science", source: "Sun", difficulty: 3,
    text: "What is the closest star to Earth?",
    options: ["Proxima Centauri", "Sirius", "The Sun", "Alpha Centauri A"], answer: 2,
    explanation: "The Sun is about 150 million kilometers away. The next nearest star, Proxima Centauri, is over 4 light-years away.",
  },
  {
    topic: "Movies & TV", source: "Jaws (film)", difficulty: 3,
    text: "Who directed the 1975 thriller Jaws?",
    options: ["Steven Spielberg", "George Lucas", "Francis Ford Coppola", "Ridley Scott"], answer: 0,
    explanation: "Steven Spielberg directed Jaws, which is often described as the first summer blockbuster.",
  },
  {
    topic: "Music & entertainment", source: "The Sound of Music", difficulty: 3,
    text: "Which musical features the song 'Do-Re-Mi'?",
    options: ["Mary Poppins", "Oklahoma!", "The Sound of Music", "My Fair Lady"], answer: 2,
    explanation: "Maria teaches the von Trapp children the song in The Sound of Music.",
  },
  {
    topic: "Art, books & culture", source: "List of languages by number of native speakers", difficulty: 3,
    text: "Which language has the most native speakers in the world?",
    options: ["English", "Spanish", "Mandarin Chinese", "Hindi"], answer: 2,
    explanation: "Mandarin Chinese has more native speakers than any other language, with Spanish in second place.",
  },
  {
    topic: "Art, books & culture", source: "Oktoberfest", difficulty: 3,
    text: "In which country did the Oktoberfest festival begin?",
    options: ["Austria", "Germany", "Switzerland", "Belgium"], answer: 1,
    explanation: "Oktoberfest began in Munich, Germany, in 1810 as a celebration of a royal wedding.",
  },
  {
    topic: "General & logic", source: "Prime number", difficulty: 3,
    text: "Which of these numbers is NOT a prime number?",
    options: ["9", "2", "5", "11"], answer: 0,
    explanation: "9 can be divided evenly by 3. The others have no divisors other than 1 and themselves.",
  },

  // Expert
  {
    topic: "Geography", source: "Strait of Gibraltar", difficulty: 4,
    text: "Which strait separates Spain from Morocco at the western end of the Mediterranean?",
    options: ["Bosphorus", "Strait of Hormuz", "Strait of Messina", "Strait of Gibraltar"], answer: 3,
    explanation: "The Strait of Gibraltar is only about 13 to 14 kilometers wide at its narrowest point.",
  },
  {
    topic: "Geography", source: "Canada–United States border", difficulty: 4,
    text: "Which two countries share the longest international border in the world?",
    options: ["Russia and Kazakhstan", "China and Mongolia", "Argentina and Chile", "Canada and the United States"], answer: 3,
    explanation: "The Canada–United States border is about 8,900 kilometers long, including the border with Alaska.",
  },
  {
    topic: "Geography", source: "Lake Baikal", difficulty: 4,
    text: "Lake Baikal, the deepest lake in the world, is in which country?",
    options: ["Russia", "Kazakhstan", "Mongolia", "China"], answer: 0,
    explanation: "Lake Baikal in Siberia is more than 1,600 meters deep and holds about a fifth of the world's fresh surface water.",
  },
  {
    topic: "History", source: "Colossus of Rhodes", difficulty: 4,
    text: "On which island did the ancient Colossus, a giant statue of the sun god Helios, stand?",
    options: ["Rhodes", "Crete", "Cyprus", "Sicily"], answer: 0,
    explanation: "The Colossus of Rhodes stood about 33 meters tall and fell in an earthquake around 226 BC.",
  },
  {
    topic: "History", source: "Mansa Musa", difficulty: 4,
    text: "Which medieval West African empire did Mansa Musa rule when he made his famous pilgrimage to Mecca in 1324?",
    options: ["Mali Empire", "Songhai Empire", "Ghana Empire", "Kanem-Bornu Empire"], answer: 0,
    explanation: "Mansa Musa ruled the Mali Empire, and his 1324 pilgrimage to Mecca was so lavish that it became legendary across the Mediterranean world.",
  },
  {
    topic: "Science", source: "Blood type", difficulty: 4,
    text: "Which blood type is known as the universal donor for red blood cells?",
    options: ["AB positive", "A positive", "B negative", "O negative"], answer: 3,
    explanation: "O negative red cells carry no A, B, or Rh markers, so they can be given to most patients in an emergency.",
  },
  {
    topic: "Science", source: "Octopus", difficulty: 4,
    text: "How many hearts does an octopus have?",
    options: ["One", "Two", "Eight", "Three"], answer: 3,
    explanation: "Two hearts pump blood through the gills, and a third pumps it around the rest of the body.",
  },
  {
    topic: "Science", source: "Mercury (element)", difficulty: 4,
    text: "Which metal is liquid at standard room temperature?",
    options: ["Gallium", "Mercury", "Lead", "Tin"], answer: 1,
    explanation: "Mercury is liquid at standard room temperature. Gallium melts at about 30 °C, just above it.",
  },
  {
    topic: "Science", source: "Stapes", difficulty: 4,
    text: "What is the smallest bone in the human body?",
    options: ["Incus", "Malleus", "Stapes", "Hyoid"], answer: 2,
    explanation: "The stapes, in the middle ear, is only about 3 millimeters long.",
  },
  {
    topic: "General & logic", source: "U.S. state", difficulty: 4,
    text: "Which letter does not appear in the name of any US state?",
    options: ["X", "J", "Z", "Q"], answer: 3,
    explanation: "No US state name contains a Q. New Jersey has a J, Arizona has a Z, and New Mexico has an X.",
  },
  {
    topic: "General & logic", source: "Cognitive reflection test", difficulty: 4,
    text: "If 5 machines take 5 minutes to make 5 widgets, how long would 100 machines take to make 100 widgets?",
    options: ["1 minute", "5 minutes", "20 minutes", "100 minutes"], answer: 1,
    explanation: "Each machine makes one widget in 5 minutes, so 100 machines make 100 widgets in the same 5 minutes.",
  },
  {
    topic: "General & logic", source: "Cognitive reflection test", difficulty: 4,
    text: "A bat and a ball cost $1.10 in total, and the bat costs $1.00 more than the ball. How much does the ball cost?",
    options: ["10 cents", "15 cents", "1 cent", "5 cents"], answer: 3,
    explanation: "If the ball costs 5 cents, the bat costs $1.05, and together they cost $1.10.",
  },
];
