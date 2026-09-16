import React from "react";
import { createRoot } from "react-dom/client";
import { ArrowUpRight } from "lucide-react";
import { products } from "./content";
import "./styles.css";
function Tile() {
  return (
    <main className="style-page">
      <div className="style-nav">
        <a className="wordmark" href="/">
          MERIDIAN
        </a>
        <a className="text-link" href="/">
          Visit the collection <ArrowUpRight size={16} />
        </a>
      </div>
      <p className="eyebrow">DESIGN LANGUAGE / 01</p>
      <h1>
        Quiet by design.
        <br />
        <em>Precise by nature.</em>
      </h1>
      <p className="style-lead">
        Tactile metal. Deep midnight. The warmth of paper. An editorial identity
        built around a simple idea: every part, a purpose.
      </p>
      <div className="style-colors">
        {[
          ["Midnight", "#101820"],
          ["Warm ivory", "#F2EFE8"],
          ["Brushed silver", "#B5BCC4"],
          ["Champagne", "#B99762"],
        ].map(([name, color]) => (
          <div className="color-tile" key={name}>
            <div style={{ background: color }} />
            <p>
              <span>{name}</span>
              <span>{color}</span>
            </p>
          </div>
        ))}
      </div>
      <div className="style-grid">
        <div className="type-sample">
          <p className="eyebrow">TYPOGRAPHY / PLAYFAIR DISPLAY + DM SANS</p>
          <h2>
            Every part,
            <br />
            <em>a purpose.</em>
          </h2>
          <p>
            Mechanical craft. Made for the hours that matter. Expressive
            editorial headings meet a calm, legible interface. Fine rules and
            open space give the product room to speak.
          </p>
          <div className="style-buttons">
            <a className="button button-dark" href="/#collection">
              Explore M01 <ArrowUpRight size={17} />
            </a>
            <a className="button button-outline" href="/#craft">
              The craft <ArrowUpRight size={17} />
            </a>
          </div>
          <div className="style-image">
            <p>
              Made for
              <br />
              <em>your everyday.</em>
            </p>
            <img
              src="/assets/generated/opening-landscape-v1.webp"
              alt="Midnight watch photographed in a dark cinematic studio"
            />
          </div>
        </div>
        <article className="product-card has-generated">
          <a
            className="product-image"
            style={{ display: "block" }}
            href="/#collection"
          >
            <span className="card-number">01 / 05</span>
            <img src={products[0].image} alt="M01 Midnight product image" />
            <span className="product-image-bottom">
              <span>The original expression</span>
              <span className="round-arrow">
                <ArrowUpRight size={19} />
              </span>
            </span>
          </a>
          <div className="product-info">
            <div>
              <h3 className="product-name">
                M01 <span>Midnight</span>
              </h3>
              <p>Brushed steel · Steel bracelet</p>
            </div>
            <span className="product-price">$895</span>
          </div>
          <div className="product-swatches">
            <span className="swatch-dot" style={{ background: "#182a3b" }} />
            <span>Midnight blue</span>
            <span className="concept-small">40 MM CASE</span>
          </div>
        </article>
      </div>
      <p className="style-footer">
        MERIDIAN is a fictional brand demonstration. Product imagery is created with Higgsfield from one consistent watch identity. Typography, layouts and motion are authored locally.
      </p>
    </main>
  );
}
createRoot(document.getElementById("root")).render(<Tile />);
