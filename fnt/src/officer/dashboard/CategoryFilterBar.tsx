import { motion } from 'framer-motion';
import React from 'react';
import { spring } from '../../ui/motion';

interface Props {
  categories: string[];
  activeCategory: string;
  onSelectCategory: (category: string) => void;
}

export const CategoryFilterBar: React.FC<Props> = ({ categories, activeCategory, onSelectCategory }) => {
  return (
    <nav
      aria-label="Product category filter"
      className="-mx-4 overflow-x-auto px-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
    >
      <div className="flex w-max items-center gap-0.5 rounded-full border border-hairline/70 bg-sunken/70 p-1">
        {categories.map((cat) => {
          const isActive = cat === activeCategory;
          return (
            <button
              key={cat}
              type="button"
              onClick={() => onSelectCategory(cat)}
              aria-pressed={isActive}
              className={`relative min-h-[40px] shrink-0 whitespace-nowrap rounded-full px-3.5 text-label transition-colors duration-base ${
                isActive ? 'text-ink' : 'text-mute hover:text-ink'
              }`}
            >
              {isActive && (
                <motion.span
                  layoutId="category-pill"
                  transition={spring.snap}
                  className="absolute inset-0 rounded-full bg-surface shadow-e1"
                />
              )}
              <span className="relative">{cat}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
