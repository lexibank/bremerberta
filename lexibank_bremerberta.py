import attr
import pylexibank
from bs4 import BeautifulSoup
from clldutils.path import Path
from clldutils.misc import slug


@attr.s
class CustomLexeme(pylexibank.Lexeme):
    AmharicGloss = attr.ib(default=None)


@attr.s
class CustomLanguage(pylexibank.Language):
    Family = attr.ib(default="Berta")


class Dataset(pylexibank.Dataset):
    dir = Path(__file__).parent
    id = "bremerberta"
    lexeme_class = CustomLexeme
    language_class = CustomLanguage

    form_spec = pylexibank.FormSpec(
        brackets={"(": ")"},
        separators="/,",
        missing_data=("?", " ", ""),
        replacements=[(" ", "_"), ("<<͡>>"[2:-2]+"tʃ", "tʃ")],
        strip_inside_brackets=True,
    )

    def cmd_download(self, args):
        with self.raw_dir.temp_download(
            "https://en.wiktionary.org/wiki/Appendix:Berta_word_lists", "raw.html"
        ) as p:
            soup = BeautifulSoup(p.read_text(encoding="utf8"), "html.parser")

        def iter_rows(table):
            yield [c.get_text().rstrip("\n") for c in table.findAll("th")]
            for row in table.findAll("tr"):
                yield [c.get_text().rstrip("\n") for c in row.findAll("td")]

        self.raw_dir.write_csv(
            "raw.csv",
            [r for r in iter_rows(soup.findAll("table", {"class": "wikitable sortable"})[0]) if r],
        )

    def cmd_makecldf(self, args):
        data = self.raw_dir.read_csv("raw.csv", dicts=True)
        languages = args.writer.add_languages(lookup_factory="Name")
        args.writer.add_sources()
        concepts = args.writer.add_concepts(
            id_factory=lambda c: c.id.split("-")[-1] + "_" + slug(c.english), lookup_factory="Name"
        )

        for row in pylexibank.progressbar(data):
            for language, lexeme in row.items():
                if language in languages:
                    args.writer.add_forms_from_value(
                        Language_ID=languages[language],
                        Parameter_ID=concepts[row["English gloss"]],
                        Value=lexeme,
                        AmharicGloss=row["Amharic gloss"],
                        Source="Bremer2016",

                    )

        # We explicitly remove the ISO column since none of the languages in
        # this dataset have an ISO code.
        args.writer.cldf["LanguageTable"].tableSchema.columns = [
            col
            for col in args.writer.cldf["LanguageTable"].tableSchema.columns
            if col.name != "ISO639P3code"
        ]
