import base64
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import io
import os

# --- IMPORTANT SIMULATION NOTES ---
# In a real production environment, you would integrate with the actual
# Google Cloud Text-to-Speech API or a specific Gemini API for audio generation.
# This 'MockAudioGen' class is a placeholder to make the backend runnable
# in isolation without needing direct external API credentials for this demo.
# It returns a very short, silent MP3 binary for demonstration purposes.

class MockAudioGen:
    def generate_audio_overview(self, query: str, source_references=None):
        """
        Mocks the audio generation process.
        In a real application, this would involve calling a Google Cloud Text-to-Speech
        API (e.g., from the google-cloud-texttospeech library) or the specific Gemini
        API for audio generation.

        For this demonstration, it returns a minimal valid MP3 byte string.
        This MP3 is essentially silent and very short, serving only to demonstrate
        the file transfer and playback mechanism.
        """
        print(f"MockAudioGen: Simulating audio generation for text: '{query[:50]}...'")

        # A very small, valid MP3 byte string (essentially silent)
        # This is a common practice for dummy audio to ensure playback works.
        # For actual speech, you'd get real audio data from a TTS service.
        dummy_mp3_data = base64.b64decode(
            "SUQzBAAAAAAAIlRTU0UAAAAPAAADTGF2ZjU4LjQ1LjEwMAAAAAAAAAAAAAAA//tExAAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAAASAAMCAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAENybWsAAAAEAElucXVpcnkAAAABAAAEkQAAACxMdmVxAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP/7xDEAAAAAABAAAAAAAAAAAAAAAAAAAAABAEluZm8AAAAAAAIAAAMQAAABqAAAAAAAAAAAHVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRVVVRPandas Data is a Python library built on top of NumPy, designed for data manipulation and analysis. It provides powerful and flexible data structures, most notably the **DataFrame**, which is a two-dimensional tabular data structure with labeled axes (rows and columns).

Here are the key features and concepts of Pandas:

1.  **DataFrame**:
    * The primary data structure in Pandas.
    * Conceptually, it's like a spreadsheet or a SQL table.
    * It consists of rows and columns, where each column can have a different data type (e.g., integer, float, string, boolean).
    * Columns are `Series` objects.
    * It allows for efficient storage and manipulation of structured data.

2.  **Series**:
    * A one-dimensional labeled array.
    * It can hold any data type (integers, floats, strings, Python objects, etc.).
    * It has an `index`, which is an array of labels for the data.
    * Think of it as a single column or a single row of a DataFrame.

3.  **Data Alignment**:
    * Pandas automatically aligns data based on labels (indices and column names) when performing operations. This means that operations between Series or DataFrames with different indices will correctly align data where labels match and introduce `NaN` (Not a Number) for missing values.

4.  **Handling Missing Data**:
    * Pandas provides tools for easily handling missing data, represented by `NaN` (Not a Number) or `NaT` (Not a Time) for datetime objects.
    * Methods like `dropna()` (to remove missing values) and `fillna()` (to fill missing values) are commonly used.

5.  **Input/Output Tools**:
    * Pandas makes it easy to read data from and write data to various file formats, including:
        * CSV (`pd.read_csv()`, `df.to_csv()`)
        * Excel (`pd.read_excel()`, `df.to_excel()`)
        * SQL databases (`pd.read_sql()`, `df.to_sql()`)
        * JSON (`pd.read_json()`, `df.to_json()`)
        * HTML tables (`pd.read_html()`, `df.to_html()`)
        * Parquet, HDF5, Feather, etc.

6.  **Data Cleaning and Preparation**:
    * Renaming columns and indices.
    * Handling duplicate data (`drop_duplicates()`).
    * Type conversion (`astype()`).
    * Applying functions to data (`apply()`, `map()`, `applymap()`).

7.  **Data Exploration and Analysis**:
    * **Selection and Indexing**: Powerful methods for selecting rows, columns, or specific cells (`loc`, `iloc`, `[]`).
    * **Filtering**: Subsetting data based on conditions.
    * **Grouping and Aggregation**: `groupby()` allows you to split data into groups based on some criteria and then apply aggregate functions (sum, mean, count, min, max, etc.) to each group.
    * **Merging and Joining**: Combining DataFrames based on common columns or indices (`merge()`, `join()`, `concat()`).
    * **Reshaping and Pivoting**: Changing the layout of tables (`pivot_table()`, `melt()`, `stack()`, `unstack()`).
    * **Time Series Functionality**: Robust tools for working with date and time data, including date ranges, frequency conversions, and lagging.

8.  **Performance**:
    * Pandas is built on top of NumPy, which means many operations are implemented in C, providing high performance.

**Why Pandas is Widely Used:**

* **Ease of Use**: Its intuitive API makes it relatively easy to get started with data manipulation.
* **Flexibility**: It can handle a wide variety of data types and structures.
* **Completeness**: It offers a comprehensive set of tools for almost every step of the data analysis workflow, from data ingestion to cleaning, transformation, analysis, and visualization (often in conjunction with libraries like Matplotlib or Seaborn).
* **Community and Ecosystem**: Large and active community, extensive documentation, and seamless integration with other Python libraries for scientific computing and machine learning.

In essence, Pandas transforms data analysis in Python from a collection of manual loops and dictionary manipulations into a more streamlined, powerful, and readable process, making it an indispensable tool for data scientists, analysts, and enginee
