function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

export function buildopendbcSiteUrl(make: string, modelOriginal: string): string {
  return `https://opendbc.com/cars/${slugify(`${make} ${modelOriginal}`)}`;
}
