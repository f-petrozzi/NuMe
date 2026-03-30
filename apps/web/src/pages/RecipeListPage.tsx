import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import {
  BookOpen,
  Clock,
  ExternalLink,
  Loader2,
  Plus,
  Save,
  Sparkles,
  TextSearch,
  Trash2,
  UtensilsCrossed,
  Wand2,
} from "lucide-react";
import { motion } from "framer-motion";

import { createRecipe, getRecommendedRecipes, getRecipes, parseRecipeText, parseRecipeUrl, type RecipeDraftInput } from "@/lib/api";
import type { ParsedRecipeDto } from "@/lib/api-contracts";
import type { Recipe } from "@/lib/types";
import { useToast } from "@/hooks/use-toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";

function formatError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  if (error instanceof Error && error.message.trim()) return error.message;
  return "Something went wrong.";
}

const RECIPE_CATEGORIES = ["Produce", "Meat", "Dairy", "Pantry", "Frozen", "Bakery", "Beverages", "Other"] as const;

const EMPTY_INGREDIENT = {
  name: "",
  quantity: "",
  category: "Other",
  section: "",
};

function normalizeParsedRecipe(recipe: ParsedRecipeDto): ParsedRecipeDto {
  return {
    title: recipe.title?.trim() || "Untitled Recipe",
    description: recipe.description?.trim() || "",
    source_url: recipe.source_url?.trim() || "",
    prep_minutes: Math.max(0, Number(recipe.prep_minutes) || 0),
    cook_minutes: Math.max(0, Number(recipe.cook_minutes) || 0),
    servings: Math.max(1, Number(recipe.servings) || 1),
    tags: (recipe.tags || []).map((tag) => String(tag).trim().toLowerCase()).filter(Boolean).slice(0, 8),
    ingredients: recipe.ingredients?.length
      ? recipe.ingredients.map((ingredient) => ({
          name: ingredient.name?.trim() || "",
          quantity: ingredient.quantity?.trim() || "",
          category: ingredient.category?.trim() || "Other",
          section: ingredient.section?.trim() || "",
        }))
      : [{ ...EMPTY_INGREDIENT }],
    instructions: recipe.instructions || "",
    photo_url: recipe.photo_url || "",
  };
}

function toRecipeInput(recipe: ParsedRecipeDto): RecipeDraftInput {
  return {
    title: recipe.title.trim() || "Untitled Recipe",
    description: recipe.description.trim(),
    source_url: recipe.source_url.trim(),
    prep_minutes: Math.max(0, Number(recipe.prep_minutes) || 0),
    cook_minutes: Math.max(0, Number(recipe.cook_minutes) || 0),
    servings: Math.max(1, Number(recipe.servings) || 1),
    tags: (recipe.tags || []).map((tag) => tag.trim().toLowerCase()).filter(Boolean).slice(0, 8),
    ingredients: (recipe.ingredients || [])
      .map((ingredient) => ({
        name: ingredient.name.trim(),
        quantity: ingredient.quantity.trim(),
        category: ingredient.category.trim() || "Other",
        section: ingredient.section.trim(),
      }))
      .filter((ingredient) => ingredient.name || ingredient.quantity),
    instructions: recipe.instructions.trim(),
    our_way_notes: "",
    photo_filename: "",
  };
}

export default function RecipeListPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { toast } = useToast();
  const [url, setUrl] = useState("");
  const [recipeText, setRecipeText] = useState("");
  const [parsedRecipe, setParsedRecipe] = useState<ParsedRecipeDto | null>(null);

  const { data: recipes = [], isLoading: recipesLoading } = useQuery({
    queryKey: ["recipes"],
    queryFn: getRecipes,
  });
  const { data: recommendedRecipes = [], isLoading: recommendedLoading } = useQuery({
    queryKey: ["recommended-recipes"],
    queryFn: getRecommendedRecipes,
  });

  const parseUrlMut = useMutation({
    mutationFn: parseRecipeUrl,
    onSuccess: (recipe) => {
      setParsedRecipe(normalizeParsedRecipe(recipe));
      toast({ title: "Recipe parsed", description: "Review the result and save it to your collection." });
    },
    onError: (error) => {
      toast({ title: "Import failed", description: formatError(error), variant: "destructive" });
    },
  });

  const parseTextMut = useMutation({
    mutationFn: parseRecipeText,
    onSuccess: (recipe) => {
      setParsedRecipe(normalizeParsedRecipe(recipe));
      toast({ title: "Recipe parsed", description: "Review the result and save it to your collection." });
    },
    onError: (error) => {
      toast({ title: "Parse failed", description: formatError(error), variant: "destructive" });
    },
  });

  const saveRecipeMut = useMutation({
    mutationFn: (recipe: ParsedRecipeDto) => createRecipe(toRecipeInput(recipe)),
    onSuccess: async (recipe) => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["recipes"] }),
        qc.invalidateQueries({ queryKey: ["recommended-recipes"] }),
      ]);
      setParsedRecipe(null);
      setUrl("");
      setRecipeText("");
      toast({ title: "Recipe saved", description: "The recipe is now available in your collection." });
      navigate(`/recipes/${recipe.id}`);
    },
    onError: (error) => {
      toast({ title: "Save failed", description: formatError(error), variant: "destructive" });
    },
  });

  const importBusy = parseUrlMut.isPending || parseTextMut.isPending;

  return (
    <div className="p-6 lg:p-10 max-w-5xl mx-auto space-y-8">
      <div className="flex items-center gap-3">
        <UtensilsCrossed className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">Recipes</h1>
          <p className="text-muted-foreground">Import new recipes and see meal matches from your latest support plan.</p>
        </div>
      </div>

      <Card className="border-primary/15 bg-primary/5">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Wand2 className="h-4 w-4 text-primary" />
            <CardTitle className="text-lg">Import A Recipe</CardTitle>
          </div>
          <CardDescription>
            Pull a recipe from the web or paste messy text, then review the parsed result before saving.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Tabs defaultValue="url" className="space-y-4">
            <TabsList>
              <TabsTrigger value="url">From URL</TabsTrigger>
              <TabsTrigger value="text">Paste Text</TabsTrigger>
            </TabsList>

            <TabsContent value="url" className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="recipe-url">Recipe URL</Label>
                <Input
                  id="recipe-url"
                  value={url}
                  onChange={(event) => setUrl(event.target.value)}
                  placeholder="https://example.com/recipe"
                />
              </div>
              <Button onClick={() => parseUrlMut.mutate(url)} disabled={importBusy || !url.trim()}>
                {parseUrlMut.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ExternalLink className="mr-2 h-4 w-4" />}
                Parse From URL
              </Button>
            </TabsContent>

            <TabsContent value="text" className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="recipe-text">Pasted Recipe Text</Label>
                <Textarea
                  id="recipe-text"
                  rows={8}
                  value={recipeText}
                  onChange={(event) => setRecipeText(event.target.value)}
                  placeholder="Paste ingredients and steps here..."
                />
              </div>
              <Button onClick={() => parseTextMut.mutate(recipeText)} disabled={importBusy || !recipeText.trim()}>
                {parseTextMut.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <TextSearch className="mr-2 h-4 w-4" />}
                Parse From Text
              </Button>
            </TabsContent>
          </Tabs>

          {parsedRecipe ? (
            <ParsedRecipeReview
              recipe={parsedRecipe}
              isSaving={saveRecipeMut.isPending}
              onChange={(nextRecipe) => setParsedRecipe(nextRecipe)}
              onSave={() => saveRecipeMut.mutate(parsedRecipe)}
              onDismiss={() => setParsedRecipe(null)}
            />
          ) : null}
        </CardContent>
      </Card>

      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <h2 className="text-lg font-semibold">Recommended For You</h2>
        </div>
        <p className="text-sm text-muted-foreground">
          These recipe matches come from the latest intervention and its meal constraints.
        </p>
        {recommendedLoading ? (
          <RecipeGridSkeleton />
        ) : recommendedRecipes.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {recommendedRecipes.map((recipe, index) => (
              <RecipeCard key={recipe.id} recipe={recipe} index={index} />
            ))}
          </div>
        ) : (
          <EmptyState
            title="No recipe matches yet"
            description="Run a check-in or scenario first, or import your own recipe below."
          />
        )}
      </section>

      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-primary" />
          <h2 className="text-lg font-semibold">Saved Recipes</h2>
        </div>
        {recipesLoading ? (
          <RecipeGridSkeleton />
        ) : recipes.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {recipes.map((recipe, index) => (
              <RecipeCard key={recipe.id} recipe={recipe} index={index} />
            ))}
          </div>
        ) : (
          <EmptyState
            title="Your recipe collection is empty"
            description="Import a recipe from the web or paste one in text form to get started."
          />
        )}
      </section>
    </div>
  );
}

function ParsedRecipeReview({
  recipe,
  isSaving,
  onChange,
  onSave,
  onDismiss,
}: {
  recipe: ParsedRecipeDto;
  isSaving: boolean;
  onChange: (recipe: ParsedRecipeDto) => void;
  onSave: () => void;
  onDismiss: () => void;
}) {
  function updateField<Key extends keyof ParsedRecipeDto>(key: Key, value: ParsedRecipeDto[Key]) {
    onChange({ ...recipe, [key]: value });
  }

  function updateIngredient(
    index: number,
    key: keyof ParsedRecipeDto["ingredients"][number],
    value: string,
  ) {
    const nextIngredients = recipe.ingredients.map((ingredient, ingredientIndex) =>
      ingredientIndex === index ? { ...ingredient, [key]: value } : ingredient,
    );
    onChange({ ...recipe, ingredients: nextIngredients });
  }

  function addIngredient() {
    onChange({
      ...recipe,
      ingredients: [...recipe.ingredients, { ...EMPTY_INGREDIENT }],
    });
  }

  function removeIngredient(index: number) {
    if (recipe.ingredients.length === 1) {
      onChange({ ...recipe, ingredients: [{ ...EMPTY_INGREDIENT }] });
      return;
    }
    onChange({
      ...recipe,
      ingredients: recipe.ingredients.filter((_, ingredientIndex) => ingredientIndex !== index),
    });
  }

  const canSave = !!recipe.title.trim();

  return (
    <div className="rounded-2xl border border-primary/20 bg-background p-5 shadow-sm">
      <div className="flex flex-col gap-3 border-b border-border pb-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <p className="text-sm font-semibold text-primary">Review Parsed Recipe</p>
          <h3 className="text-xl font-semibold">{recipe.title}</h3>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Adjust anything the parser got wrong before saving.
          </p>
          <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
            <span>{recipe.prep_minutes + recipe.cook_minutes} min total</span>
            <span>{recipe.servings} serving{recipe.servings === 1 ? "" : "s"}</span>
            <span>{recipe.ingredients.filter((ingredient) => ingredient.name.trim()).length} ingredients</span>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onDismiss} disabled={isSaving}>
            Dismiss
          </Button>
          <Button onClick={onSave} disabled={isSaving || !canSave}>
            {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
            Save Recipe
          </Button>
        </div>
      </div>

      <div className="mt-5 space-y-5">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="parsed-title">Title</Label>
            <Input
              id="parsed-title"
              value={recipe.title}
              onChange={(event) => updateField("title", event.target.value)}
              placeholder="Recipe title"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="parsed-source">Source URL</Label>
            <Input
              id="parsed-source"
              value={recipe.source_url}
              onChange={(event) => updateField("source_url", event.target.value)}
              placeholder="https://example.com/recipe"
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="parsed-description">Description</Label>
          <Textarea
            id="parsed-description"
            rows={3}
            value={recipe.description}
            onChange={(event) => updateField("description", event.target.value)}
            placeholder="Short description"
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-4">
          <div className="space-y-2">
            <Label htmlFor="parsed-prep">Prep Minutes</Label>
            <Input
              id="parsed-prep"
              type="number"
              min={0}
              value={recipe.prep_minutes}
              onChange={(event) => updateField("prep_minutes", Math.max(0, Number(event.target.value) || 0))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="parsed-cook">Cook Minutes</Label>
            <Input
              id="parsed-cook"
              type="number"
              min={0}
              value={recipe.cook_minutes}
              onChange={(event) => updateField("cook_minutes", Math.max(0, Number(event.target.value) || 0))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="parsed-servings">Servings</Label>
            <Input
              id="parsed-servings"
              type="number"
              min={1}
              value={recipe.servings}
              onChange={(event) => updateField("servings", Math.max(1, Number(event.target.value) || 1))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="parsed-tags">Tags</Label>
            <Input
              id="parsed-tags"
              value={recipe.tags.join(", ")}
              onChange={(event) =>
                updateField(
                  "tags",
                  event.target.value
                    .split(",")
                    .map((tag) => tag.trim().toLowerCase())
                    .filter(Boolean)
                    .slice(0, 8),
                )
              }
              placeholder="quick, pasta, vegetarian"
            />
          </div>
        </div>

        <div className="space-y-3 rounded-xl border border-border/80 bg-muted/20 p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold">Ingredients</p>
              <p className="text-xs text-muted-foreground">Fix quantities, sections, and categories before saving.</p>
            </div>
            <Button type="button" variant="outline" onClick={addIngredient}>
              <Plus className="mr-2 h-4 w-4" />
              Add Row
            </Button>
          </div>

          <div className="hidden grid-cols-[1.7fr_1fr_1fr_1fr_auto] gap-2 px-1 text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground md:grid">
            <span>Name</span>
            <span>Quantity</span>
            <span>Category</span>
            <span>Section</span>
            <span className="sr-only">Remove</span>
          </div>

          <div className="space-y-3">
            {recipe.ingredients.map((ingredient, index) => (
              <div
                key={`${index}-${ingredient.name}-${ingredient.quantity}`}
                className="grid gap-2 rounded-xl border border-border/70 bg-background p-3 md:grid-cols-[1.7fr_1fr_1fr_1fr_auto] md:items-start"
              >
                <Input
                  value={ingredient.name}
                  onChange={(event) => updateIngredient(index, "name", event.target.value)}
                  placeholder="Ingredient name"
                />
                <Input
                  value={ingredient.quantity}
                  onChange={(event) => updateIngredient(index, "quantity", event.target.value)}
                  placeholder="1 tbsp"
                />
                <select
                  value={ingredient.category}
                  onChange={(event) => updateIngredient(index, "category", event.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  {RECIPE_CATEGORIES.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </select>
                <Input
                  value={ingredient.section}
                  onChange={(event) => updateIngredient(index, "section", event.target.value)}
                  placeholder="Sauce"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => removeIngredient(index)}
                  className="shrink-0"
                >
                  <Trash2 className="h-4 w-4" />
                  <span className="sr-only">Remove ingredient</span>
                </Button>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-2 rounded-xl border border-border/80 bg-muted/20 p-4">
          <Label htmlFor="parsed-instructions" className="text-sm font-semibold">
            Instructions
          </Label>
          <Textarea
            id="parsed-instructions"
            rows={10}
            value={recipe.instructions}
            onChange={(event) => updateField("instructions", event.target.value)}
            placeholder={"One step per line.\nUse ## Section Name for grouped sections."}
          />
          <p className="text-xs text-muted-foreground">
            Keep one step per line. Prefix section headers with <code>##</code> if the recipe has grouped instructions.
          </p>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {recipe.tags.map((tag) => (
            <Badge key={tag} variant="outline" className="text-xs">
              {tag}
            </Badge>
          ))}
        </div>
      </div>
    </div>
  );
}

function RecipeCard({ recipe, index }: { recipe: Recipe; index: number }) {
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.06 }}>
      <Link
        to={`/recipes/${recipe.id}`}
        className="block rounded-xl border border-border bg-card p-5 shadow-sm transition-shadow hover:shadow-md"
      >
        <h3 className="mb-1 font-semibold">{recipe.title}</h3>
        <p className="mb-3 line-clamp-2 text-sm text-muted-foreground">{recipe.description}</p>
        <div className="mb-3 flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {recipe.prep_time + recipe.cook_time} min
          </span>
          <span>{recipe.servings} serving{recipe.servings > 1 ? "s" : ""}</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {recipe.tags.map((tag) => (
            <Badge key={tag} variant="outline" className="text-xs">
              {tag}
            </Badge>
          ))}
        </div>
      </Link>
    </motion.div>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-xl border border-dashed border-border bg-muted/30 p-6 text-center">
      <p className="font-medium">{title}</p>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

function RecipeGridSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {[0, 1].map((item) => (
        <div key={item} className="h-40 animate-pulse rounded-xl bg-muted" />
      ))}
    </div>
  );
}
