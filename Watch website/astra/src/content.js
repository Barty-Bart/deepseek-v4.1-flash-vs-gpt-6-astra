export const brand = {
  name: "MERIDIAN",
  tagline: "Every part, a purpose.",
  founded: 2018,
  story:
    "Meridian began in 2018 with a simple question: what does a watch really need? Our answer is a considered balance of form, function and the quiet pleasure of a mechanical movement. Designed to be worn often. And kept for the years ahead.",
  disclosure: "Fictional brand concept — illustrative figures",
  stats: [
    { value: "8", label: "Years of design" },
    { value: "12,400", label: "Watches sold" },
    { value: "9,800", label: "Owners" },
  ],
};
export const products = [
  {
    id: "midnight",
    family: "M01",
    name: "Midnight",
    color: "#182a3b",
    dial: "Midnight blue",
    price: 895,
    material: "Brushed steel · Steel bracelet",
    image: "/assets/generated/product-midnight-v1.webp",
    hoverImage: "/assets/generated/product-midnight-wrist-v1.webp",
    note: "The original expression",
    description:
      "A deep blue dial that shifts with the light. Brushed steel, precise proportions and just enough detail. An everyday companion, considered from every angle.",
  },
  {
    id: "ivory",
    family: "M01",
    name: "Ivory",
    color: "#ded7c5",
    dial: "Warm ivory",
    price: 895,
    material: "Brushed steel · Steel bracelet",
    image: "/assets/generated/product-ivory-v1.webp",
    hoverImage: "/assets/generated/product-ivory-wrist-v1.webp",
    note: "Clarity in every hour",
    description:
      "A warm ivory dial brings a softer perspective to the M01. Silver indices and a fine champagne seconds hand give every glance a quiet sense of clarity.",
  },
  {
    id: "forest",
    family: "M01",
    name: "Forest",
    color: "#233e34",
    dial: "Dark forest",
    price: 895,
    material: "Brushed steel · Steel bracelet",
    image: "/assets/generated/product-forest-v1.webp",
    hoverImage: "/assets/generated/product-forest-wrist-v1.webp",
    note: "A different kind of depth",
    description:
      "Dark forest green meets the cool precision of brushed steel. A subtle departure, with the familiar balance and everyday comfort of the M01.",
  },
  {
    id: "eclipse",
    family: "M01",
    name: "Eclipse",
    color: "#353638",
    dial: "Charcoal",
    price: 945,
    material: "Dark coated steel · Steel bracelet",
    image: "/assets/generated/product-eclipse-v1.webp",
    hoverImage: "/assets/generated/product-eclipse-wrist-v1.webp",
    note: "An exercise in restraint",
    description:
      "A charcoal dial and dark coated steel give the M01 a more understated presence. Tonal details reveal themselves slowly, as the light moves.",
  },
  {
    id: "atelier",
    family: "M02",
    name: "Atelier",
    color: "#bfa579",
    dial: "Champagne",
    price: 795,
    material: "Brushed steel · Cognac leather",
    image: "/assets/generated/product-atelier-v1.webp",
    hoverImage: "/assets/generated/product-atelier-wrist-v1.webp",
    note: "Warmth, by design",
    description:
      "A champagne dial paired with a supple cognac leather strap. The same considered case architecture, with a warmer character for the everyday.",
  },
];
export const specifications = [
  ["Movement", "Automatic mechanical"],
  ["Case diameter", "40 mm"],
  ["Crystal", "Sapphire"],
  ["Power reserve", "40 hours"],
  ["Water resistance", "100 m"],
  ["Reference time", "10:10"],
];
export const money = (value) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
export const navigation = [
  ["Collection", "collection"],
  ["Craft", "craft"],
  ["Our Story", "about"],
  ["Trade In", "trade-in"],
];
