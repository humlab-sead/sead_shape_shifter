#!/bin/bash

g_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
g_target_dir="$(cd "${g_script_dir}/../lib" && pwd)"

set -e

echo "Installing UCanAccess package..."

function download_ucanaccess() {
    rm -rf "${g_target_dir}/ucanaccess"

    tmp_dir=$(mktemp -d)

    pushd "${tmp_dir}"

    echo "Downloading UCanAccess to temporary directory ${tmp_dir}..."
    wget https://sourceforge.net/projects/ucanaccess/files/latest/download -O ucanaccess.zip
    cp /tmp/ucanaccess.zip  "${tmp_dir}"
    unzip ucanaccess.zip -d ucanaccess_extracted

    download_folder=$(ls "${tmp_dir}/ucanaccess_extracted" | head -n 1)
    echo ${download_folder}
    popd

    mv "${tmp_dir}/ucanaccess_extracted/${download_folder}" "${g_target_dir}/ucanaccess"
    rm -rf "${tmp_dir}"
    echo "UCanAccess installed in ${g_target_dir}/ucanaccess"
}

download_ucanaccess
