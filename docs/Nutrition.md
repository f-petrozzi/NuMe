# Nutrition Project

## Purpose

This file is a reference for the new wellness app based on what already worked in Nest.

It is intentionally not a build plan or a design spec.

The new app context is:

- large user base
- no households
- one user account per end user
- wellness product, not a couples dashboard
- combines wearable health data, nutrition, recipes, meal planning, and workout guidance

This document focuses mostly on:

- Garmin ingestion and health structures
- recipe parsing and recipe display structures

It only records patterns that already worked in Nest and are worth preserving as product knowledge.

## Context Change Relative To Nest

Nest was built around two named people and a shared household UI.

That means these Nest assumptions do not carry over directly:

- `person_a` / `person_b`
- shared meal ownership
- household competition as a core concept
- fragment-based tabs inside a larger app shell

The parts that do carry over well are:

- Garmin token bootstrap and sync flow
- health data storage shape
- cache-first health reads from the database
- recipe URL import flow
- pasted recipe parsing flow
- recipe detail data model
- meal-plan linkage to recipes
- basic nutrition log linkage to health data

## MVP Features Already Proven In Nest

### Garmin and health

These already worked end to end in Nest:

- Garmin account bootstrap with MFA support
- persistent Garmin OAuth token cache on disk
- background scheduled sync
- manual sync trigger
- daily summary metrics
- sleep history
- recent activities
- simple trend charts
- manual food log
- calorie view that combines food log with Garmin calories burned

### Recipe parsing

These already worked in Nest:

- import recipe from URL
- parse pasted recipe text
- parse first, review manually, then save
- preserve source URL
- optional recipe photo from upload or imported image URL

### Recipe display

These already worked in Nest:

- searchable recipe list
- tag filtering
- recipe cards with photo, timing, and servings
- recipe detail view
- grouped ingredient sections
- grouped instruction sections
- source link
- notes field

### Meal planning

The recipe linkage already worked in Nest:

- weekly slots
- slot-to-recipe relation
- custom meal override when no recipe is selected
- recipe title and description shown from the linked recipe
- grocery generation from recipe ingredients

### AI features already lightly proven in Nest

These worked in a limited way:

- pasted recipe text parsing through Gemini
- AI calorie estimate for a single food item
- structured JSON extraction from AI responses

## Garmin Structures That Already Worked In Nest

## Garmin connection and bootstrap flow

Nest used a flow that worked reliably enough for a real user setup:

1. credentials were configured outside the app
2. a separate bootstrap script handled Garmin MFA
3. OAuth token files were written to a persistent token directory
4. app startup loaded token-backed Garmin clients
5. runtime request handlers never talked to Garmin directly
6. all user-facing reads came from the database

Important details from Nest:

- token cache used two files:
  - `oauth1_token.json`
  - `oauth2_token.json`
- token cache directories were separated by logical person key:
  - `person_a`
  - `person_b`
- passwords could come from secret files
- cached tokens allowed startup without a live password

For the new app, the proven part is the token-cache flow itself, not the two-person naming.

## Garmin sync responsibilities that worked

Nest kept the Garmin sync logic in one dedicated module:

- initialize authenticated Garmin clients
- fetch daily health metrics
- fetch sleep data
- fetch recent activities
- upsert into local storage
- write sync audit rows
- publish refresh events after a successful sync

The request handlers did not do any direct Garmin network work.

That separation worked well.

## Garmin metrics that Nest already pulled successfully

Nest synced these metrics:

- steps
- step goal
- active calories
- total calories
- resting heart rate
- average heart rate
- body battery high
- body battery low
- stress average
- intensity minutes
- floors climbed
- SpO2 average
- HRV weekly average
- HRV status
- VO2 max
- active minutes
- sleep score
- sleep stage durations
- activities and activity metadata

## Health database shape that already worked in Nest

### `health_profiles`

Purpose in Nest:

- per-person goals
- light profile metadata for health settings

Columns used in practice:

- `person`
- `daily_step_goal`
- `daily_calorie_goal`
- `garmin_user_id`
- `updated_at`

### `health_daily_metrics`

Purpose in Nest:

- one daily summary row per person per date
- primary source for overview cards and trend charts

Columns used:

- `person`
- `metric_date`
- `steps`
- `step_goal`
- `active_calories`
- `total_calories`
- `resting_hr`
- `avg_hr`
- `body_battery_high`
- `body_battery_low`
- `stress_avg`
- `intensity_minutes_moderate`
- `intensity_minutes_vigorous`
- `floors_climbed`
- `spo2_avg`
- `hrv_weekly_avg`
- `hrv_status`
- `vo2_max`
- `active_minutes`
- `raw_json`
- `synced_at`

Important behavior:

- unique key was effectively `(person, metric_date)`
- upsert behavior worked well for repeated syncs
- this table was the main read source for dashboard-like views

### `health_sleep_sessions`

Purpose in Nest:

- one row per person per sleep date
- support both summary and detailed sleep display

Columns used:

- `person`
- `sleep_date`
- `sleep_start`
- `sleep_end`
- `duration_seconds`
- `deep_seconds`
- `light_seconds`
- `rem_seconds`
- `awake_seconds`
- `sleep_score`
- `avg_spo2`
- `avg_respiration`
- `raw_json`
- `synced_at`

### `health_activities`

Purpose in Nest:

- recent workouts and activity history
- activity feed

Columns used:

- `person`
- `garmin_activity_id`
- `activity_type`
- `activity_name`
- `start_time`
- `duration_seconds`
- `distance_meters`
- `calories`
- `avg_hr`
- `max_hr`
- `elevation_gain_meters`
- `avg_speed_mps`
- `training_load`
- `raw_json`
- `synced_at`

Important behavior:

- unique key was effectively `(person, garmin_activity_id)`
- a single range fetch then upsert worked well

### `health_sync_runs`

Purpose in Nest:

- sync audit trail
- status visibility
- operational debugging

Columns used:

- `person`
- `status`
- `sync_type`
- `started_at`
- `finished_at`
- `metrics_upserted`
- `activities_upserted`
- `sleep_upserted`
- `error_text`
- `details_json`

This table was useful operationally and should be preserved conceptually.

### `health_calorie_log`

Purpose in Nest:

- manual food log
- combine food intake with Garmin burn metrics

Columns used:

- `person`
- `log_date`
- `meal_type`
- `food_name`
- `calories`
- `quantity`
- `notes`
- `ai_estimated`
- `created_by`
- `created_at`

This worked well as a simple manual-entry nutrition layer.

## Garmin read behavior that already worked in Nest

Nest used these read patterns successfully:

- health overview came from the local database only
- trends came from the local database only
- sleep history came from the local database only
- activities came from the local database only
- food log combined local nutrition rows with local Garmin-derived calorie rows

That cache-first model was one of the cleanest parts of the Nest health feature.

## Health API shape that already worked in Nest

Nest exposed these health routes:

- `GET /overview`
- `GET /competition`
- `GET /daily`
- `GET /sleep`
- `GET /activities`
- `GET /profile`
- `PUT /profile`
- `GET /calorie-log`
- `POST /calorie-log`
- `DELETE /calorie-log/{id}`
- `GET /calorie-log/ai-estimate`
- `POST /sync`
- `GET /sync/status`
- `GET /garmin/auth-status`
- `POST /garmin/authenticate`

Not all of that routing shape needs to be reused, but these are the concrete capabilities that already existed.

## Garmin frontend behavior that already worked in Nest

Nest's health UI had five working sub-views:

- Overview
- Activity
- Sleep
- Nutrition
- Trends

Within those views, the most useful behaviors were:

- fast overview cards from synced local data
- simple recent activity feed
- sleep grouped in a readable history layout
- calorie log by meal type
- trend chart toggles across a small metric set

The Nest health UI also worked well with:

- manual sync button
- live refresh after sync
- loading recent data first instead of forcing a full refresh

## Recipe Structures That Already Worked In Nest

## Canonical recipe row shape from Nest

Nest stored recipes in one main `recipes` table.

Columns used:

- `id`
- `title`
- `description`
- `source_url`
- `our_way_notes`
- `prep_minutes`
- `cook_minutes`
- `servings`
- `tags`
- `ingredients`
- `instructions`
- `photo_filename`
- `created_by`
- `created_at`

What worked well:

- the row had enough structure to support import, manual editing, detail display, and meal planning
- `source_url` was useful for provenance
- `our_way_notes` was useful for user-specific adaptation
- `photo_filename` was enough for local media support

## Ingredient structure that already worked in Nest

Nest stored ingredients as JSON.

Each ingredient object looked like:

```json
{
  "name": "all-purpose flour",
  "quantity": "2 cups",
  "category": "Pantry",
  "section": "Cake"
}
```

Fields that mattered in practice:

- `name`
- `quantity`
- `category`
- `section`

Why this worked:

- `quantity` as free text preserved recipe language well
- `section` allowed grouped ingredient display
- `category` allowed grocery generation and basic organization

The `section` field was especially useful.

## Instruction structure that already worked in Nest

Nest stored instructions as a newline-separated text blob.

The display contract was:

- one instruction step per line
- optional section headers encoded as lines starting with `## `

Example:

```text
## Make the sauce
Blend tomatoes and garlic.
Simmer for 10 minutes.
## Assemble
Layer pasta and sauce.
Bake until golden.
```

Why this worked:

- simple to parse and render
- easy to generate from imported content
- easy to edit manually
- section headers were preserved without needing a separate step table

This format was one of the cleanest proven recipe display contracts in Nest.

## Tag structure that already worked in Nest

Nest stored tags as a JSON array of short strings.

Example:

```json
["pasta", "quick", "vegetarian"]
```

This worked fine for:

- filtering
- display chips
- user editing

## Recipe parsing flow that already worked in Nest

### URL import flow

Nest's URL import flow worked well because it was layered:

1. unwrap known print-service wrapper URLs
2. validate scheme and hostname
3. reject local/private/blocked destinations
4. revalidate redirect targets
5. fetch HTML with byte limits
6. parse using `recipe-scrapers`
7. prefer structured instruction extraction from JSON-LD
8. prefer grouped ingredient extraction from known recipe-plugin HTML
9. fall back to scraper-provided groups or raw ingredients
10. hand the parsed result to the manual review UI before saving

This overall flow was strong and should be preserved as product knowledge.

### What Nest specifically extracted from imported recipe URLs

Nest extracted:

- title
- description
- source URL
- prep minutes
- cook minutes
- servings
- instructions
- ingredients
- image URL

### Instruction extraction behavior that worked

Nest's best instruction results came from this priority order:

1. JSON-LD extraction from `recipeInstructions`
2. scraper instruction list
3. scraper instruction text

JSON-LD extraction was valuable because it preserved section names and step ordering better than many generic scrapers.

### Ingredient extraction behavior that worked

Nest's best ingredient results came from this priority order:

1. known grouped HTML patterns
2. scraper ingredient groups
3. scraper raw ingredient strings

Nest explicitly handled grouped ingredient HTML from:

- Tasty Recipes
- WP Recipe Maker

That grouped extraction produced noticeably better detail pages than flat ingredient lists.

### Quantity handling that worked

Nest split leading quantity text from ingredient name using a regex.

That let it normalize inputs like:

- `2 cups flour`
- `1 tbsp olive oil`
- `220g chocolate`

The proven behavior was:

- preserve quantity as human-readable text
- do not over-normalize
- do not try to turn recipe imports into strict nutrition measurements too early

### Pasted recipe parsing flow that already worked

Nest used Gemini for pasted recipe text.

The prompt asked for structured JSON with:

- `title`
- `description`
- `prep_minutes`
- `cook_minutes`
- `servings`
- `ingredients`
- `instructions`
- `tags`

The important part was not the exact prompt wording.

The important part was the workflow:

1. user pasted messy recipe text
2. AI returned structured data
3. Nest normalized the result
4. user reviewed the result manually
5. only then was the recipe saved

That review-before-save step was important and already worked.

## Recipe photo flow that already worked in Nest

Nest supported:

- manual image upload
- importing a photo from a remote image URL
- saving the image locally and linking it to the recipe row

Validation that already worked:

- content-type validation
- magic-byte validation for image uploads
- byte limits
- safe filename generation

## Recipe display behavior that already worked in Nest

## Recipe list

Nest's recipe list supported:

- text search by title
- tag chip filtering
- card display
- photo preview
- prep + cook total time
- servings

That was a simple but effective browse surface.

## Recipe detail view

Nest's detail view worked well because it showed:

- title
- image
- total time
- servings
- tags
- grouped ingredients
- grouped instructions
- notes
- source link

The grouped ingredient and grouped instruction display was the strongest part of the recipe UI.

## Ingredient section rendering that worked

Nest grouped ingredients by `section`.

That supported patterns like:

- Sauce
- Filling
- Topping
- Marinade

This made imported recipes feel much closer to the source material.

## Instruction section rendering that worked

Nest treated `## ` lines as section headers and all other lines as numbered steps.

That gave a simple display rule:

- section headers render unnumbered
- non-header lines render as numbered steps

This was easy to maintain and worked well in practice.

## Ingredient reference behavior that worked in Nest

Nest had an extra display feature that was useful:

- instruction text could highlight ingredient names
- hovering or tapping showed the linked ingredient quantity

This worked through:

- a searchable ingredient index built from ingredient names
- optional manual override mapping stored client-side

The valuable part was not the exact storage method.

The valuable part was the concept that recipe instructions can reference ingredient measurements directly in the UI.

## Meal planning structures that already worked in Nest

Nest linked recipes into a simple `meal_plan_slots` table.

Columns used:

- `plan_date`
- `meal_type`
- `recipe_id`
- `custom_name`
- `notes`
- `created_by`

Related behavior that worked:

- recipe selection from the recipe catalog
- custom meal when no recipe exists
- display of recipe title and description from the linked recipe
- grocery generation from linked recipe ingredients

This is still relevant even in a single-user app because recipe-to-plan linkage already worked well.

## Nutrition recommendation-adjacent behavior already proven in Nest

Nest did not have a full recommendation engine, but these adjacent pieces already existed:

- health metrics were stored cleanly enough to drive readiness-like logic
- calorie intake and Garmin calorie burn could be compared for the day
- recipe data had enough structure to support future meal suggestions
- AI already returned structured JSON for recipe parsing

The strongest current foundation for recommendations is:

- synced wearable metrics
- manual food log
- structured recipe catalog

## External Integrations That Already Worked In Nest

## Garmin Connect

Used for:

- daily summary metrics
- sleep
- activities

What worked operationally:

- token cache on disk
- startup initialization
- background sync
- no Garmin calls inside request handlers

## recipe-scrapers

Used for:

- URL-based recipe parsing

What worked:

- broad baseline compatibility
- useful metadata extraction
- good fallback layer even when custom extraction was also present

## HTML and JSON-LD extraction

Used for:

- better instruction extraction
- better grouped ingredient extraction

This was an important supplement to generic scraping.

## Gemini

Used for:

- pasted recipe text parsing
- simple calorie estimation

What worked:

- requesting structured JSON
- validating and normalizing the result before using it

## Frontend support libraries

Nest also relied on:

- Chart.js for health trends
- Alpine for the feature state
- Lucide for icons

Those are implementation details, but the underlying UI behaviors are already proven.

## Migration Notes From Nest

This section only records what can be moved cleanly from Nest into the new app.

## Garmin data that can be imported directly

These Nest datasets are already coherent enough to migrate:

- `health_daily_metrics`
- `health_sleep_sessions`
- `health_activities`
- `health_sync_runs`
- `health_calorie_log`

What to preserve during migration:

- metric dates
- all parsed scalar health fields
- activity IDs
- sleep dates
- sync status history
- raw payload references when available

## Garmin token state that can be reused

Nest's token cache format is already useful.

What to preserve:

- token directory contents
- link between token cache and the end user account
- auth-status visibility

The person-key naming from Nest is not important.

The token lifecycle is.

## Recipe data that can be imported directly

These fields are already useful as-is:

- title
- description
- source_url
- our_way_notes
- prep_minutes
- cook_minutes
- servings
- tags
- ingredients
- instructions
- photo_filename
- created_at

The most important recipe migration details to preserve are:

- `section` on ingredients
- newline step ordering
- `## ` section-header convention in instructions
- source URL provenance
- uploaded image linkage

## Meal-planning data that can be imported directly

These are already portable:

- slot date
- meal type
- linked recipe
- custom name
- notes

## Things from Nest that are proven, but Nest-specific

These existed in Nest and worked there, but they are Nest-specific rather than product requirements:

- two-person comparison views
- `person_a` and `person_b` naming
- shared household assumptions
- health tab under `/api/health-data`
- fragment loading inside the Nest shell
- localStorage-only ingredient-link overrides

They should be treated as Nest implementation context, not core product knowledge.

## Short Reference Summary

If another model is building the new app and only needs the most important proven takeaways from Nest, they are:

- Garmin worked best when auth/bootstrap, sync, storage, and reads were clearly separated.
- Health reads worked best when every user-facing view read from local synced tables, never live from Garmin.
- The most useful health tables were daily summaries, sleep sessions, activities, sync runs, and a simple calorie log.
- Recipe imports worked best when URL parsing was layered: safe fetch, structured extraction, grouped ingredient extraction, then manual review.
- The recipe structure that worked best was:
  - tags as string array
  - ingredients as structured rows with `name`, `quantity`, `category`, `section`
  - instructions as newline text with optional `## ` section headers
- Recipe detail display worked well when grouped ingredients and grouped instruction sections were preserved.
- Meal planning already benefited from simple recipe linkage without needing a complex planning model.

That is the strongest Nest-derived foundation for the new wellness app.