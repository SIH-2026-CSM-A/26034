import React from 'react';

interface Props {
  categories: string[];
  activeCategory: string;
  onSelectCategory: (category: string) => void;
}

export const CategoryFilterBar: React.FC<Props> = ({
  categories,
  activeCategory,
  onSelectCategory,
}) => {
  return (
    <nav
      aria-label="Product category filter"
      className="w-full overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
    >
      <div className="flex items-center gap-1.5">
        <span className="shrink-0 text-xs font-bold uppercase tracking-widest text-slate-500 mr-1">
          Filter:
        </span>
        {categories.map((cat) => {
          const isActive = cat === activeCategory;
          return (
            <button
              key={cat}
              type="button"
              onClick={() => onSelectCategory(cat)}
              aria-pressed={isActive}
              className={`shrink-0 px-3 py-1 text-xs font-semibold rounded-full border transition-all duration-150 ${
                isActive
                  ? 'bg-indigo-600 text-white border-indigo-700 shadow-sm'
                  : 'bg-white text-slate-600 border-slate-300 hover:border-indigo-400 hover:text-indigo-700 hover:bg-indigo-50'
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
