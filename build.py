import datetime
import html
from importlib.resources import contents
import os
from turtle import title
from types import new_class
from typing import List
import shutil
import re
from functools import lru_cache
import glob

TIMESTAMP_NOW = datetime.datetime.now().strftime("%Y-%m-%d")
HERE = os.path.dirname(os.path.abspath(__file__))
print(HERE)

src_root_garden = os.path.join(HERE, "digital-garden")
src_root_blog = os.path.join(HERE, "blog")
src_root_pages = os.path.join(HERE, "pages")
src_root_images = os.path.join(HERE, "images")
build_root = os.path.join(HERE, "build")

with open(os.path.join(HERE, "header.html"), "r", encoding="utf-8") as fh:
    header_html = fh.read()

with open(os.path.join(HERE, "footer.html"), "r", encoding="utf-8") as fh:
    footer_html = fh.read()


class BlogPost:
    def __init__(self, contents: str, file_name: str, category=""):
        self.category = category
        self.file_name = file_name
        self.html_name = file_name[:-4]
        self.file = ""
        self.title = ""
        self.date = ""
        self.description = ""
        self.tags: List[str] = []
        self.body_lines = []
        self.body_lines_formatted = []
        self.body_type = ""
        self.is_starred = False
        self.url = []
        self.updated = ""

        capture_body = False
        lines = contents.splitlines()
        for line_no_strip in lines:
            line = line_no_strip.rstrip()
            if capture_body:
                self.body_lines.append(line_no_strip)
            elif line.startswith("title:"):
                self.title = line[6:].strip()
            elif line.startswith("file:"):
                self.file = line[5:].strip()
                self.url = [self.file]
            elif line.startswith("url:"):
                url = line[4:].strip()
                url = url.split(",")
                self.url = [u.strip() for u in url if u.strip()]
                self.url = [u + "?ref=andrewshay.me" for u in self.url]
            elif line.startswith("date:"):
                self.date = line[5:].strip()
            elif line.startswith("updated:"):
                self.updated = line[8:].strip()
            elif line.startswith("description:"):
                self.description = line[12:].strip()
            elif line.startswith("star:"):
                self.is_starred = True
            elif line.startswith("tags:"):
                self.tags = line[5:].strip()
                self.tags = self.tags.split(",")
                self.tags = [tag.strip() for tag in self.tags]
                self.tags = [tag.lower() for tag in self.tags if tag]
            elif line.startswith("body:"):
                capture_body = True
                self.body_type = line[5:].strip()
            else:
                assert False, f"Unknown key '{line}' for '{self.file_name}'"

        if self.body_type == "":
            self.body_type = "custom"
        elif self.body_type != "html":
            assert (
                False
            ), f"Incorrect body type '{self.body_type}' for '{self.file_name}'"

        if not self.updated:
            self.updated = self.date

        self.format_body()

    def __str__(self) -> str:
        return f"{self.__class__.__name__} - {self.title}"

    def format_body(self):
        if self.body_type == "html":
            self.body_lines_formatted = self.body_lines
            return

        url_pattern = r"(\[.+\])(\(.+\))"
        img_pattern = r"(!\[.+\])(\(.+\))"
        formatted_lines = []
        is_code_block = False
        for line_no_strip in self.body_lines:
            line = line_no_strip.strip()

            new_line = line_no_strip
            if is_code_block and line.startswith("```"):
                new_line = "</pre>"
                is_code_block = False
            elif line.startswith("```") and not is_code_block:
                new_line = '<pre class="code-pre">'
                is_code_block = True
            elif is_code_block:
                new_line = html.escape(new_line)
            elif line.startswith("####"):
                new_line = line[4:].strip()
                new_line = f"<h4>{new_line}</h4>"
            elif line.startswith("###"):
                new_line = line[3:].strip()
                new_line = f"<h3>{new_line}</h3>"
            elif line.startswith("##"):
                new_line = line[2:].strip()
                new_line = f"<h2>{new_line}</h2>"
            elif line.startswith("#"):
                new_line = line[1:].strip()
                new_line = f"<h1>{new_line}</h1>"
            else:
                img_pattern = r"((!\[.+\])(\(.+\)))"
                url_pattern = r"((\[.+\])(\(.+\)))"
                i_pattern = r"(__.*?__)"
                strong_pattern = r"(\*\*.*\*\*)"
                code_pattern = r"(`.+?`)"
                # 0=img total group / 1=img text / 2=img link / 3=url group / 4=url text / 5=url link / 6=code text / 7=i text / 8=strong text /
                combine = (
                    img_pattern
                    + r"|"
                    + url_pattern
                    + r"|"
                    + code_pattern
                    + r"|"
                    + i_pattern
                    + r"|"
                    + strong_pattern
                )
                match = re.findall(combine, new_line)

                if match:
                    for m in match:
                        if m[0]:
                            img_alt = m[1][2:-1]
                            img_src = m[2][1:-1]
                            if img_src.startswith("http"):
                                new_text = f'<img alt="{img_alt}" src="{img_src}">'
                            else:
                                new_text = f'<img alt="{img_alt}" src="{{ROOT}}images/{img_src}">'
                            new_line = new_line.replace(m[0], new_text)

                        if m[3]:
                            url_text = m[4][1:-1]
                            url_href = m[5][1:-1]
                            new_text = f'<a href="{url_href}">{url_text}</a>'
                            new_line = new_line.replace(m[3], new_text)

                        if m[6]:
                            code_text = m[6][1:-1]
                            new_line = new_line.replace(
                                m[6], f"<code>{code_text}</code>"
                            )

                        if m[7]:
                            i_text = m[7][2:-2]
                            new_line = new_line.replace(m[7], f"<i>{i_text}</i>")

                        if m[8]:
                            strong_text = m[8][2:-2]
                            new_line = new_line.replace(
                                m[8], f"<strong>{strong_text}</strong>"
                            )

                if (
                    not new_line.startswith("<li>")
                    and not new_line.startswith("<ol>")
                    and not new_line.startswith("</ol>")
                    and not new_line.startswith("<ul>")
                    and not new_line.startswith("</ul>")
                ):
                    new_line += "<br/>"

            formatted_lines.append(new_line)

        self.body_lines_formatted = formatted_lines


class Category:
    def __init__(self, contents: str, file_name: str) -> None:
        self.file_name = file_name
        self.html_name = self.file_name[:-4]

        lines = contents.splitlines()
        self.title = lines[0].strip()
        assert self.title.startswith("title:"), self.title
        self.title = self.title[6:].strip()
        assert self.title

        self.icon = lines[1].strip()
        assert self.icon.startswith("icon:"), self.icon
        self.icon = self.icon[5:].strip()
        assert self.icon

        self.entries: List[BlogPost] = []

        # Remove header info, like title
        lines = lines[3:]
        collected_lines = []
        collect = False
        for line_no_strip in lines:
            line = line_no_strip.strip()

            if line == "---##":
                if collect:
                    assert (
                        False
                    ), f"Collect found while already collecting. Missing end marker. {self.file_name} {line}"
                collect = True
            elif line == "---!##":
                entry_contents = "\n".join(collected_lines)
                self.entries.append(
                    BlogPost(entry_contents, "fakefile.txt", category=self.html_name)
                )
                collected_lines = []
                collect = False
            elif collect:
                collected_lines.append(line_no_strip)
            elif line == "":
                continue
            else:
                assert False, f"{self.title} failed line, '{line_no_strip}'"

        self.entries = sorted(self.entries, key=lambda x: x.title.lower())

        assert self.entries

    def __str__(self):
        return f"<{self.__class__.__name__} - {self.title} - {len(self.entries)}>"


def read_blogs():
    blog_posts = []
    for file_name in os.listdir(src_root_blog):
        with open(os.path.join(src_root_blog, file_name), "r", encoding="utf-8") as f:
            contents = f.read()
        post = BlogPost(contents, file_name)
        blog_posts.append(post)

    blog_posts = sorted(blog_posts, key=lambda x: x.date, reverse=True)
    return blog_posts


def read_garden():
    categories = []
    for file_name in os.listdir(src_root_garden):
        with open(os.path.join(src_root_garden, file_name), "r", encoding="utf-8") as f:
            contents = f.read()
            categories.append(Category(contents, file_name))

    categories = sorted(categories, key=lambda x: x.title.lower())
    return categories


def get_blog_block(blog_posts: List[BlogPost], root, limit=None, add_more_link=False):
    blog_block = """\n<section>
<h1>💭 Blog</h1>
<div class="h1-line"></div>
<div class="blog-listing">
"""
    url = root + "blog/"
    counter = 0
    limit = limit or len(blog_posts)
    for index, post in enumerate(blog_posts[:limit]):
        if counter == 0:
            blog_block += '\n\n<div class="row">'

        post_url = url + post.html_name
        blog_block += """
        <div class="column2">
            {num}. <a class="blog-listing-a" style="padding-bottom: 1rem;" href="{post_url}/">{title}</a>
        </div>     
""".format(
            title=post.title, num=index + 1, post_url=post_url
        )

        if counter == 1:
            blog_block += "</div>"
            counter = 0
        else:
            counter += 1

    more_link = ""
    if add_more_link:
        more_link = f'<div id="blog-more" style="width: 100%;"><a style="text-decoration: none; padding-right: 2em;" href="{root}blog">More...</a></div>'
    blog_block += f"""
</div>
{more_link}
<!--blog-listing-->
</section>
"""
    return blog_block


def get_logo_row_block(root="./"):
    html = '<div class="logo-row">\n'
    html += f'  <a href="https://github.com/Andrew-Shay"><img class="logo-img" src="{root}images/logo_github.svg" alt="GitHub Profile" /></a>\n'
    html += f'  <a href="https://techhub.social/@andrewshay"><img class="logo-img" src="{root}images/logo_mastodon.svg" alt="Mastodon Profile" /></a>\n'
    html += f'  <a href="#" id="discord-logo-link"><img class="logo-img" src="{root}images/logo_discord.svg" alt="Discord Profile" /></a>\n'
    html += f'  <a href="https://bsky.app/profile/andrewshay.bsky.social"><img class="logo-img" src="{root}images/logo_bluesky.svg" alt="BlueSky Profile" /></a>\n'
    html += '</div>\n'
    html += '''
<div id="discord-popup" class="discord-popup" style="display:none;">
  <div class="discord-popup-content">
    <span id="discord-popup-close" class="discord-popup-close" title="Close">&times;</span>
    <div id="discord-popup-text">
      <strong>Username:</strong> <span id="discord-username">Andrew_Shay#8923</span><br>
      <small>Click to copy</small>
    </div>
  </div>
</div>
<script>
document.addEventListener("DOMContentLoaded", function() {
  var link = document.getElementById("discord-logo-link");
  var popup = document.getElementById("discord-popup");
  var close = document.getElementById("discord-popup-close");
  var text = document.getElementById("discord-popup-text");
  var username = document.getElementById("discord-username");
  if(link && popup && close) {
    link.addEventListener("click", function(e) {
      e.preventDefault();
      popup.style.display = "flex";
    });
    close.addEventListener("click", function() {
      popup.style.display = "none";
    });
    window.addEventListener("click", function(e) {
      if(e.target === popup) popup.style.display = "none";
    });
    text.style.cursor = "pointer";
    text.addEventListener("click", function() {
        navigator.clipboard.writeText(username.textContent);
        username.textContent = "Copied!";
        setTimeout(function() {
          username.textContent = "Andrew_Shay#8923";
        }, 1000);
      });
  }
});
</script>
'''
    return html


def get_garden_block(categories: List[Category], root):
    garden_block = """<section>
    <h1><span class='post-icon'>🌱</span> Digital Garden</h1>
    <div class="h1-line"></div>
"""
    url = root + "digital-garden/"
    counter = 0
    bubble_counter = 0
    for index, category in enumerate(categories):
        title = category.title
        count = len(category.entries)

        if counter == 0:
            garden_block += '\n\n<div class="row">'

        bubble_class = "tag-bubble"
        if bubble_counter in (2, 3):
            bubble_class = "tag-bubble tag-bubble-even"

        post_url = url + category.html_name
        icon = category.icon
        garden_block += """
        <div class="column2">
            <a class="tag-bubble-a" href="{post_url}">
                <div class="{bubble_class}">{icon} {title} ({count})</div>
            </a>
        </div>
""".format(
            title=title,
            count=count,
            post_url=post_url,
            icon=icon,
            bubble_class=bubble_class,
        )

        if counter == 1:
            garden_block += "</div>"
            counter = 0
        else:
            counter += 1

        if bubble_counter == 3:
            bubble_counter = 0
        else:
            bubble_counter += 1

    #garden_block += "</div>"

    # Get latest and starred
    # Remove duplicate titles
    # Sort by date - newest to oldest
    all_entries: List[BlogPost] = []
    titles = []
    for category in categories:
        all_entries.extend(category.entries)
    all_entries = sorted(all_entries, key=lambda x: x.date, reverse=True)

    no_dupe_entries: List[BlogPost] = []
    titles = []
    for entry in all_entries:
        title = entry.title
        if title not in titles:
            titles.append(title)
            no_dupe_entries.append(entry)

    starred_entries = [entry for entry in no_dupe_entries if entry.is_starred]
    starred_entries = starred_entries[:9]

    min_count = 9 if 9 > len(starred_entries) else len(starred_entries)
    newest_entries = no_dupe_entries[:min_count]

    garden_block += """
    <div class="row" style="text-align: center; padding-top: 2rem;">
            <div class="column2">
            <h3 style="font-variant: small-caps;">📡 Newest Entries</h3>
                        <ol>
"""
    garden_block += f'<li><a href="https://transmitic.net/?ref=andrewshay.me" title="Transmitic">Transmitic</a></li>'
    for entry in newest_entries:
        url = (
            f"{root}digital-garden/{entry.category}/{entry.file}"
            if entry.body_lines_formatted
            else entry.url[0]
        )
        garden_block += f'<li><a href="{url}" title="{html.escape(entry.description or entry.title)}">{entry.title}</a></li>'

    garden_block += """
        </ol>
        </div>
        <div class="column2">
            <h3 style="font-variant: small-caps;">⭐ Starred Entries</h3>
            <ol>
"""
    garden_block += f'<li><a href="https://transmitic.net/?ref=andrewshay.me"  title="Transmitic">Transmitic</a></li>'
    for entry in starred_entries:
        garden_block += f'<li><a href="{entry.url[0]}"  title="{html.escape(entry.description or entry.title)}">{entry.title}</a></li>'

    garden_block += """
    </ol>
        </div>
    </div></section>
"""

    return garden_block


def write_index(blog_posts, categories: List[Category]):
    webring = """
<section style="text-align:center; padding-top: 2rem;">
<a href="https://hotlinewebring.club/andrew-shay/previous">← Previous Site</a>
<a style="padding-left:1rem;padding-right: 1rem;" href="https://hotlinewebring.club/">Hotline Webring</a>
<a href="https://hotlinewebring.club/andrew-shay/next">Next Site →</a>
<a style="display: none;" rel="me" href="https://techhub.social/@andrewshay">Mastodon</a>
</section>    
"""

    index_path = os.path.join(build_root, "index.html")
    root = "./"

    header = header_html.format(
        ROOT=root,
        TITLE="Home",
        DESCRIPTION="Andrew Shay's Blog and Digital Garden",
        OGURL="",
        UPDATED_TIME=TIMESTAMP_NOW,
    )

    blog_block = get_blog_block(blog_posts, root, limit=10, add_more_link=True)
    logo_row_block = get_logo_row_block(root)
    garden_block = get_garden_block(categories, root)

    html = f"{header} {blog_block} {logo_row_block} {garden_block} {webring} {footer_html}"

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)


def write_blog(blog_posts: List[BlogPost], root):
    # write index
    blog_block = get_blog_block(blog_posts, root)
    build_blog_root = os.path.join(build_root, "blog")
    os.makedirs(build_blog_root)

    blog_path = os.path.join(build_blog_root, "index.html")

    header = header_html.format(
        ROOT=root,
        TITLE="Blog",
        DESCRIPTION="Andrew Shay's Blog",
        OGURL="blog",
        UPDATED_TIME=TIMESTAMP_NOW,
    )

    html = f"{header} {blog_block} {footer_html}"

    with open(blog_path, "w", encoding="utf-8") as f:
        f.write(html)

    # write posts
    root = "../../"
    for post in blog_posts:
        post_path = os.path.join(build_blog_root, post.html_name)
        os.makedirs(post_path)

        description = post.description or post.title
        header = header_html.format(
            ROOT=root,
            TITLE=post.title,
            DESCRIPTION=description,
            OGURL=f"blog/{post.html_name}",
            UPDATED_TIME=post.updated,
        )
        post_html = "\n".join(post.body_lines_formatted)
        post_html = post_html.replace("{ROOT}", root)
        post_date_update = (
            f' &nbsp;&nbsp;&nbsp;&nbsp;(updated <span itemprop="dateModified" content="{post.updated}T00:00:00+00:00">{post.updated}</span>)'
            if post.updated != post.date
            else ""
        )
        post_date_block = (
            f'<div class="blog-date"><span itemprop="datePublished" content="{post.date}T00:00:00+00:00">{post.date}</span>{post_date_update}</div>'
            if post.date
            else ""
        )
        breadcrumbs = f'<a href="{root}">Home</a> &gt; <a href="{root}blog">Blog</a> &gt; {post.title[:30]}...'
        author = '<meta itemprop="author" content="Andrew Shay" />'
        post_html = f'{header}{breadcrumbs}<br><br>\n<article itemscope itemtype="https://schema.org/BlogPosting"><h1 itemprop="headline">{post.title}</h1><div class="h1-line"></div>{post_date_block}{author}<div itemprop="articleBody">{post_html}</div></article>\n{footer_html}'

        post_index_path = os.path.join(post_path, "index.html")
        assert not os.path.exists(post_index_path), post_index_path
        with open(post_index_path, "w", encoding="utf-8") as f:
            f.write(post_html)


def write_garden(categories: List[Category], root):
    # write index
    blog_block = get_garden_block(categories, root)
    build_blog_root = os.path.join(build_root, "digital-garden")
    os.makedirs(build_blog_root)

    blog_path = os.path.join(build_blog_root, "index.html")

    header = header_html.format(
        ROOT=root,
        TITLE="Digital Garden",
        DESCRIPTION="Andrew Shay's Digital Garden",
        OGURL="digital-garden",
        UPDATED_TIME=TIMESTAMP_NOW,
    )

    html = f"{header} {blog_block} {footer_html}"
    assert not os.path.exists(blog_path), blog_path
    with open(blog_path, "w", encoding="utf-8") as f:
        f.write(html)

    # write posts
    root = "../../"
    for post in categories:
        post_path = os.path.join(build_blog_root, post.html_name)
        os.makedirs(post_path)

        entries = post.entries[:]
        latest_timestamp = max([entry.updated for entry in entries])

        description = post.title
        header = header_html.format(
            ROOT=root,
            TITLE=post.title,
            DESCRIPTION=description,
            OGURL=f"digital-garden/{post.html_name}",
            UPDATED_TIME=latest_timestamp,  # TODO
        )

        post_html = "<ol>"

        starred_entres = [e for e in entries if e.is_starred]
        starred_entres = sorted(starred_entres, key=lambda x: x.title.lower())
        other = [e for e in entries if not e.is_starred]
        other = sorted(other, key=lambda x: x.title.lower())

        entries = starred_entres + other

        for index, entry in enumerate(entries):
            entry_description = entry.description if entry.description else entry.title

            if entry.body_lines_formatted:
                eheader = header_html.format(
                    ROOT=root,
                    TITLE=entry.title,
                    DESCRIPTION=entry_description,
                    OGURL=f"digital-garden/{post.html_name}/{entry.file}",
                    UPDATED_TIME=entry.updated,
                )
                html = "\n".join(entry.body_lines_formatted)

                breadcrumbs = f'<a href="{root}">Home</a> &gt; <a href="{root}digital-garden">Digital Garden</a> &gt; <a href="{root}digital-garden/{post.html_name}">{post.title}</a> &gt; {entry.title[:30]}...'
                post_date_update = (
                    f' &nbsp;&nbsp;&nbsp;&nbsp;(updated <span itemprop="dateModified" content="{entry.updated}T00:00:00+00:00">{entry.updated}</span>)'
                    if entry.updated != entry.date
                    else ""
                )
                post_date_block = (
                    f'<div class="blog-date"><span itemprop="datePublished" content="{entry.date}T00:00:00+00:00">{entry.date}</span>{post_date_update}</div>'
                    if entry.date
                    else ""
                )
                author = '<meta itemprop="author" content="Andrew Shay" />'
                html = f'{eheader}{breadcrumbs}<br><br>\n<article itemscope itemtype="https://schema.org/BlogPosting"><h1 itemprop="headline">{entry.title}</h1><div class="h1-line"></div>{post_date_block}{author}<div itemprop="articleBody">{html}</div></article>\n{footer_html}'

                p = os.path.join(post_path, entry.file)
                assert not os.path.exists(p), p
                with open(p, "w", encoding="utf-8") as f:
                    f.write(html)

            star = "⭐" if entry.is_starred else ""
            icon = "📝" if entry.file else "🔗"
            if entry.file:  # This is a note
                href = f"{root}digital-garden/{post.html_name}/{entry.file}"
            else:
                href = entry.url[0]

            desc = '<div class="desc">'
            if len(entry.url) > 1:
                for index, u in enumerate(entry.url[1:]):
                    desc += f'<div>({index+2}) <a href="{u}">{u}</a></div>'

            desc += f"{entry.description}" if entry.description else ""
            desc += "</div>"
            post_html += f'<li style="padding-bottom: 1.2rem;">{star} {icon} <a href="{href}">{entry.title}</a>{desc}</li>'
        post_html += "</ol>"

        post_html = post_html.replace("{ROOT}", root)
        breadcrumbs = f'<a href="{root}">Home</a> &gt; <a href="{root}digital-garden">Digital Garden</a> &gt; {post.title}'
        post_html = f"{header}{breadcrumbs}<br><br><h1><span class='post-icon'>{post.icon}</span> {post.title} ({len(post.entries)})</h1><div class='h1-line'></div>{post_html}{footer_html}"

        post_index_path = os.path.join(post_path, "index.html")
        assert not os.path.exists(post_index_path), post_index_path
        with open(post_index_path, "w", encoding="utf-8") as f:
            f.write(post_html)


def write_pages(root):
    pages = []
    for file_name in os.listdir(os.path.join(HERE, "pages")):
        file_path = os.path.join(HERE, "pages", file_name)
        with open(file_path, "r", encoding="utf-8") as f:
            contents = f.read()

        new_name = file_name[:-4]
        new_path = os.path.join(build_root, new_name)
        os.makedirs(new_path)
        index_path = os.path.join(new_path, "index.html")

        post = BlogPost(contents, file_name)
        pages.append(post)

        description = post.description or post.title
        header = header_html.format(
            ROOT=root,
            TITLE=post.title,
            DESCRIPTION=description,
            OGURL=new_name,
            UPDATED_TIME=post.updated,
        )
        post_html = "\n".join(post.body_lines_formatted)
        post_html = post_html.replace("{ROOT}", root)
        post_date_block = (
            f'<div class="blog-date">{post.date}</div>' if post.date else ""
        )
        post_html = f"{header}<h1>{post.title}</h1><div class='h1-line'></div>{post_date_block}{post_html}{footer_html}"

        assert not os.path.exists(index_path), index_path
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(post_html)

    return pages


def write_feed(blog_posts: List[BlogPost]):
    from datetime import datetime
    import time

    date_time = datetime.fromtimestamp(time.time())
    str_date_time = date_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    str_date_time_sitemap = date_time.strftime("%Y-%m-%d")

    feed_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">

  <title>Andrew Shay's Blog and Digital Garden</title>
  <link href="https://andrewshay.me"/>
  <link href="https://andrewshay.me/feed.xml" rel="self"/>
  <updated>{str_date_time}</updated>
  <author>
    <name>Andrew Shay</name>
  </author>
  <id>andrewshay.me</id>
"""

    for post in blog_posts:
        body = "\n".join(post.body_lines_formatted)
        body = html.escape(body)
        feed_xml += f"""
<entry>
    <title>{post.title}</title>
    <link href="https://andrewshay.me/blog/{post.html_name}"/>
    <id>{post.file_name}</id>
    <updated>{post.updated}</updated>
    <content type="html">
        {body}
    </content>
</entry>
        """

    feed_xml += "</feed>"

    feed_path = os.path.join(build_root, "feed.xml")
    with open(feed_path, "w", encoding="utf-8") as f:
        f.write(feed_xml)

    return str_date_time_sitemap

def write_sitemap(blog_posts: List[BlogPost], categories: List[Category], pages: List[BlogPost], feed_date: str):
        sitemap = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    """
        # Add blog posts to sitemap
        updated = []
        for post in blog_posts:
            updated.append(post.updated)
            sitemap += f"""
        <url>
            <loc>https://andrewshay.me/blog/{html.escape(post.html_name)}/index.html</loc>
            <lastmod>{post.updated}</lastmod>
        </url>
    """
        latest = max(updated)
        sitemap += f"""
        <url>
            <loc>https://andrewshay.me/blog/index.html</loc>
            <lastmod>{latest}</lastmod>
        </url>
    """

        # Add categories to sitemap
        updated = []
        for category in categories:
            cat_updated = []

            for entry in category.entries:
                cat_updated.append(entry.updated)
                updated.append(entry.updated)
                if entry.file:
                    sitemap += f"""
        <url>
            <loc>https://andrewshay.me/digital-garden/{html.escape(category.html_name)}/{html.escape(entry.file)}</loc>
            <lastmod>{entry.updated}</lastmod>
        </url>
    """
            latest = max(cat_updated)
            sitemap += f"""
        <url>
            <loc>https://andrewshay.me/digital-garden/{html.escape(category.html_name)}/index.html</loc>
            <lastmod>{latest}</lastmod>
        </url>
    """
                    
        latest = max(updated)
        sitemap += f"""
        <url>
            <loc>https://andrewshay.me/digital-garden/index.html</loc>
            <lastmod>{latest}</lastmod>
        </url>
    """           
        
        for page in pages:
            sitemap += f"""
        <url>
            <loc>https://andrewshay.me/{html.escape(page.html_name)}/index.html</loc>
            <lastmod>{page.updated}</lastmod>
        </url>
    """
            
        sitemap += f"""
        <url>
            <loc>https://andrewshay.me/feed.xml</loc>
            <lastmod>{feed_date}</lastmod>
        </url>
    """
        sitemap += "</urlset>"
    
        sitemap_path = os.path.join(build_root, "sitemap.xml")
        with open(sitemap_path, "w", encoding="utf-8") as f:
            f.write(sitemap)

def main():
    blog_posts = read_blogs()
    for post in blog_posts:
        print(post)
    categories = read_garden()
    for category in categories:
        print(category)
        for entry in category.entries:
            print(f"\t{entry}")

    if os.path.exists(build_root):
        shutil.rmtree(build_root)
    os.makedirs(build_root)

    shutil.copy2(os.path.join(HERE, "style.css"), os.path.join(build_root, "style.css"))
    shutil.copytree(os.path.join(HERE, "images"), os.path.join(build_root, "images"))

    write_index(blog_posts, categories)
    write_blog(blog_posts, "../")
    write_garden(categories, "../")
    pages = write_pages("../")
    feed_date = write_feed(blog_posts)
    write_sitemap(blog_posts, categories, pages, feed_date)

if __name__ == "__main__":
    main()
