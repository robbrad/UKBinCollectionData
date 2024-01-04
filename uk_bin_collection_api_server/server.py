# server.py

import connexion
from uk_bin_collection.uk_bin_collection.collect_data import UKBinCollectionApp
import logging
import traceback


def council_data(
    council,
    url,
    postcode=None,
    uprn=None,
    house_number=None,
    usrn=None,
    skip_get_url=False,
    web_driver=None,
):
    args = [council, url]

    if uprn:
        args.append(f"-u={uprn}")
    if postcode:
        args.append(f"-p={postcode}")
    if house_number:
        args.append(f"-n={house_number}")
    if usrn:
        args.append(f"-us={usrn}")

    if web_driver:
        args.append(f"-w={web_driver}")
    if skip_get_url is True:
        args.append(f"-s")

    try:
        CollectData = UKBinCollectionApp()
        CollectData.set_args(args)
        return CollectData.run()
    except Exception as err:
        logging.error(traceback.format_exc())
        logging.info(f"Schema: {err}")
        raise err


def create_app():
    app = connexion.App(__name__, specification_dir="./")
    app.add_api("swagger.yaml")
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080)
