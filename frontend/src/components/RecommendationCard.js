/**
 * RecommendationCard.js
 * Displays a single AI-sourced product recommendation.
 */

import React from "react";
import "./RecommendationCard.css";

/**
 * @param {object} props
 * @param {{
 *   title: string,
 *   price: string,
 *   image_url: string,
 *   product_url: string,
 *   retailer: string,
 *   why_it_matches?: string
 * }} props.item
 */
export default function RecommendationCard({ item }) {
  const { title, price, image_url, product_url, retailer, why_it_matches } = item;

  return (
    <div className="rec-card">
      <div className="rec-image-wrap">
        {image_url ? (
          <img src={image_url} alt={title} className="rec-image" loading="lazy" />
        ) : (
          <div className="rec-image-placeholder">No image</div>
        )}
      </div>
      <div className="rec-body">
        <p className="rec-name">{title}</p>
        {retailer && <p className="rec-retailer">{retailer}</p>}
        {price && <p className="rec-price">{price}</p>}
        {why_it_matches && (
          <p className="rec-why">{why_it_matches}</p>
        )}
        {product_url && (
          <a
            href={product_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary rec-btn"
          >
            Shop Now
          </a>
        )}
      </div>
    </div>
  );
}
