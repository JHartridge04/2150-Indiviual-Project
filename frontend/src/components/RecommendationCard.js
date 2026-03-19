/**
 * RecommendationCard.js
 * Displays a single clothing recommendation with image, name, price, and a link.
 */

import React from "react";
import "./RecommendationCard.css";

/**
 * @param {object} props
 * @param {{ name: string, image: string, price: string, link: string }} props.item
 */
export default function RecommendationCard({ item }) {
  const { name, image, price, link } = item;

  return (
    <div className="rec-card">
      <div className="rec-image-wrap">
        <img src={image} alt={name} className="rec-image" loading="lazy" />
      </div>
      <div className="rec-body">
        <p className="rec-name">{name}</p>
        <p className="rec-price">{price}</p>
        <a
          href={link}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-primary rec-btn"
        >
          Shop Now
        </a>
      </div>
    </div>
  );
}
