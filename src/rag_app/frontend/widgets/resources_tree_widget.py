from textual.widgets import Tree
from pathlib import Path


class ResourcesTreeWidget(Tree[str]):
    def __init__(self, resources_paths: list[str], *args, **kwargs):
        super().__init__("Saved resources", *args, **kwargs)
        self.resources_paths = resources_paths

    def on_mount(self) -> None:
        self.root.expand()

        built_nodes = {"": self.root}

        for path_str in sorted(self.resources_paths):
            path = Path(path_str)
            current_path_key = ""

            for i, part in enumerate(path.parts):
                parent_key = current_path_key
                current_path_key = (
                    f"{current_path_key}/{part}" if current_path_key else part
                )

                # add the node if not already added
                if current_path_key not in built_nodes:
                    is_last_part = i == len(path.parts) - 1

                    if is_last_part:
                        built_nodes[current_path_key] = built_nodes[
                            parent_key
                        ].add_leaf(f"📄 {part}")
                    else:
                        built_nodes[current_path_key] = built_nodes[parent_key].add(
                            f"📁 {part}"
                        )
