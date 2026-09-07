import React from 'react';

interface Props {
  categories: string[];
  activeCategory: string;
  onSelectCategory: (category: string) => void;
}

export const CategoryFilterBar: React.FC<Props> = ({ categories, activeCategory, onSelectCategory }) => {
  return (
    <nav aria-label="Product category filter" className="w-full overflow-x-auto pb-1">
      <div className="flex items-center gap-2 min-w-max">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-700 mr-1">Category Axis:</span>
        {categories.map((cat) => {
          const isActive = cat === activeCategory;
          return (
            <button
              key={cat}
              type="button"
              onClick={() => onSelectCategory(cat)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                isActive
                  ? 'bg-slate-900 text-white border-2 border-slate-950 shadow-xs'
                  : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-100'
              }`}
            >
              {cat}
            </button>
          );
        })}
      </div>
    </nav>
  );
};
