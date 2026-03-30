import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Clock, ExternalLink, Sparkles, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { getRecipe } from "@/lib/api";
import type { RecipeIngredient } from "@/lib/types";

type IngredientIndexEntry = {
  ingredient: RecipeIngredient;
  searchTerms: string[];
};

type AnnotatedStepPart =
  | { type: "text"; text: string }
  | { type: "ingredient"; text: string; ingredient: RecipeIngredient };

const INGREDIENT_STOP_WORDS = new Set([
  "fresh",
  "large",
  "small",
  "medium",
  "extra",
  "virgin",
  "finely",
  "roughly",
  "thinly",
  "softened",
  "melted",
  "chopped",
  "diced",
  "minced",
  "sliced",
  "grated",
  "crushed",
  "ground",
  "dried",
  "cooked",
  "raw",
  "optional",
  "plus",
  "more",
  "about",
  "and",
  "or",
  "of",
  "a",
  "an",
  "the",
  "to",
  "cup",
  "cups",
  "tbsp",
  "tsp",
  "tablespoon",
  "tablespoons",
  "teaspoon",
  "teaspoons",
  "pound",
  "pounds",
  "ounce",
  "ounces",
  "gram",
  "grams",
  "kg",
  "lb",
  "oz",
  "ml",
  "liter",
  "liters",
]);

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function buildIngredientIndex(ingredients: RecipeIngredient[]): IngredientIndexEntry[] {
  return ingredients
    .map((ingredient) => {
      const normalized = ingredient.name
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, " ")
        .replace(/\s+/g, " ")
        .trim();

      if (!normalized) return null;

      const words = normalized.split(" ").filter((word) => word.length > 1);
      const coreWords = words.filter((word) => !INGREDIENT_STOP_WORDS.has(word) && word.length > 2);
      const terms = new Set<string>();

      terms.add(normalized);
      if (coreWords.length > 0) {
        terms.add(coreWords.join(" "));
        terms.add(coreWords[coreWords.length - 1]);
      }
      if (coreWords.length >= 2) {
        terms.add(coreWords.slice(-2).join(" "));
      }

      const searchTerms = [...terms].filter((term) => term.length > 2).sort((a, b) => b.length - a.length);
      if (!searchTerms.length) return null;

      return { ingredient, searchTerms };
    })
    .filter((entry): entry is IngredientIndexEntry => entry !== null);
}

function annotateInstructionStep(step: string, ingredientIndex: IngredientIndexEntry[]): AnnotatedStepPart[] {
  if (!step || !ingredientIndex.length) return [{ type: "text", text: step }];

  const candidates = ingredientIndex.flatMap((entry) =>
    entry.searchTerms.map((term) => ({
      ingredient: entry.ingredient,
      priority: term.length,
      term,
    })),
  );
  candidates.sort((a, b) => b.priority - a.priority);

  const ranges: Array<{ start: number; end: number; ingredient: RecipeIngredient }> = [];

  for (const candidate of candidates) {
    const regex = new RegExp(`\\b(${escapeRegExp(candidate.term)}(?:e?s)?)\\b`, "gi");
    let match: RegExpExecArray | null = null;

    while ((match = regex.exec(step)) !== null) {
      const start = match.index;
      const end = start + match[0].length;
      if (ranges.some((range) => start < range.end && end > range.start)) continue;
      ranges.push({ start, end, ingredient: candidate.ingredient });
    }
  }

  if (!ranges.length) return [{ type: "text", text: step }];

  ranges.sort((a, b) => a.start - b.start);

  const parts: AnnotatedStepPart[] = [];
  let cursor = 0;

  for (const range of ranges) {
    if (range.start > cursor) {
      parts.push({ type: "text", text: step.slice(cursor, range.start) });
    }
    parts.push({
      type: "ingredient",
      text: step.slice(range.start, range.end),
      ingredient: range.ingredient,
    });
    cursor = range.end;
  }

  if (cursor < step.length) {
    parts.push({ type: "text", text: step.slice(cursor) });
  }

  return parts;
}

function InstructionStepText({
  step,
  ingredientIndex,
}: {
  step: string;
  ingredientIndex: IngredientIndexEntry[];
}) {
  const parts = annotateInstructionStep(step, ingredientIndex);

  return (
    <>
      {parts.map((part, index) => {
        if (part.type === "text") return <span key={`text-${index}`}>{part.text}</span>;

        return (
          <span key={`ingredient-${index}-${part.text}`} className="group relative inline">
            <span
              tabIndex={0}
              className="cursor-help font-medium text-foreground underline decoration-primary/70 decoration-dotted underline-offset-4 outline-none transition-colors hover:text-primary focus-visible:text-primary"
            >
              {part.text}
            </span>
            <span className="pointer-events-none absolute left-1/2 top-full z-20 mt-2 hidden w-52 -translate-x-1/2 rounded-xl border border-border bg-background px-3 py-2 text-left shadow-xl group-hover:block group-focus-within:block">
              <span className="block text-sm font-semibold text-primary">
                {part.ingredient.quantity || "To taste"}
              </span>
              <span className="block text-xs text-foreground/85">{part.ingredient.name}</span>
              {part.ingredient.section ? (
                <span className="mt-1 block text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  {part.ingredient.section}
                </span>
              ) : null}
            </span>
          </span>
        );
      })}
    </>
  );
}

export default function RecipeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: recipe } = useQuery({ queryKey: ["recipe", id], queryFn: () => getRecipe(id!), enabled: !!id });

  if (!recipe) {
    return (
      <div className="mx-auto max-w-4xl p-6 lg:p-10">
        <div className="h-64 animate-pulse rounded-3xl bg-muted" />
      </div>
    );
  }

  const ingredientIndex = buildIngredientIndex(recipe.ingredient_items);
  const showIngredientGroupLabels = Boolean(
    recipe.ingredients.length > 1 || (recipe.ingredients[0]?.group && recipe.ingredients[0].group !== "Ingredients"),
  );
  const showInstructionGroupLabels = Boolean(
    recipe.instructions.length > 1 || (recipe.instructions[0]?.group && recipe.instructions[0].group !== "Steps"),
  );
  const sourceUrl = recipe.source_url.match(/^https?:\/\//) ? recipe.source_url : `https://${recipe.source_url}`;

  return (
    <div className="mx-auto max-w-3xl space-y-8 p-6 lg:p-10">
      <Link to="/recipes" className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to recipes
      </Link>

      {recipe.image_url ? (
        <img
          src={recipe.image_url}
          alt={recipe.title}
          className="h-64 w-full rounded-3xl border border-border/80 object-cover shadow-sm"
        />
      ) : null}

      <section className="space-y-4">
        <div>
          <h1 className="mb-2 text-2xl font-bold tracking-tight lg:text-3xl">{recipe.title}</h1>
          {recipe.description ? (
            <p className="max-w-2xl text-sm leading-6 text-muted-foreground">{recipe.description}</p>
          ) : null}
        </div>

        <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Clock className="h-4 w-4" />
            {recipe.prep_time + recipe.cook_time} min
          </span>
          <span className="flex items-center gap-1.5">
            <Users className="h-4 w-4" />
            {recipe.servings} serving{recipe.servings > 1 ? "s" : ""}
          </span>
        </div>

        {recipe.tags.length ? (
          <div className="flex flex-wrap gap-1.5">
            {recipe.tags.map((tag) => (
              <Badge key={tag} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        ) : null}
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-bold">Ingredients</h2>
        {recipe.ingredients.map((group) => (
          <div key={group.group || "Ingredients"} className="space-y-2">
            {showIngredientGroupLabels ? (
              <h3 className="text-sm font-semibold text-muted-foreground">{group.group || "Ingredients"}</h3>
            ) : null}
            <ul className="space-y-2">
              {group.items.map((item, index) => (
                <li key={`${group.group}-${item.name}-${index}`} className="flex items-start gap-3 text-sm leading-6">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                  <span className="min-w-[5.75rem] shrink-0 font-medium text-primary/80">
                    {item.quantity || "To taste"}
                  </span>
                  <span className="text-foreground/90">{item.name}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-bold">Instructions</h2>
          <span className="text-xs text-muted-foreground">Hover underlined ingredients for quantities</span>
        </div>

        {recipe.instructions.map((group) => (
          <div key={group.group} className="space-y-3">
            {showInstructionGroupLabels ? (
              <h3 className="text-sm font-semibold text-muted-foreground">{group.group}</h3>
            ) : null}

            <ol className="space-y-3">
              {group.steps.map((step, index) => (
                <li key={`${group.group}-${index}`} className="flex items-start gap-3 text-sm leading-6">
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-semibold text-accent-foreground">
                    {index + 1}
                  </span>
                  <p className="text-foreground/90">
                    <InstructionStepText step={step} ingredientIndex={ingredientIndex} />
                  </p>
                </li>
              ))}
            </ol>
          </div>
        ))}
      </section>

      {(recipe.our_way_notes || recipe.source_url) ? (
        <section className="space-y-4 border-t border-border pt-6">
          {recipe.our_way_notes ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Sparkles className="h-4 w-4 text-primary" />
                <span>Our Way</span>
              </div>
              <p className="text-sm leading-6 text-muted-foreground">{recipe.our_way_notes}</p>
            </div>
          ) : null}

          {recipe.source_url ? (
            <a
              href={sourceUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 text-sm text-primary hover:underline"
            >
              <ExternalLink className="h-4 w-4" />
              Open original recipe
            </a>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
