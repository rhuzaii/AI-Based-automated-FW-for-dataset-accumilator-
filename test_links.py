from utils.web_link_finder import find_links

links = find_links("boarding pass image", max_links=10)

print("\nRESULT LINKS:")
for l in links:
    print(l)