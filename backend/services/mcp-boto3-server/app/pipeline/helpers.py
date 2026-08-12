def extract_source_paths(deployment_data: dict, source: str):
    paths = []

    for section in deployment_data.get("sections", []):
        for control in section.get("controls", []):
            for dp in control.get("deployment_points", []):
                path = dp.get("path")

                if not path:
                    continue

                if source == "aws" and path.startswith("s3://"):
                    paths.append(path)

                elif source == "local" and not path.startswith("s3://"):
                    paths.append(path)

                elif source == "gitlab" and "gitlab" in path.lower():
                    paths.append(path)

    return list(set(paths))