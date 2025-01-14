# Chess

## Overview
This project is a creative attempt to build a user-friendly interface for a fun and engaging game of Chess. The color palettes and animations draw inspiration from popular chess platforms like lichess.org and chess.com. In addition to player-versus-player functionality, the game includes an inbuilt AI opponent with an approximate strength of 1200 ELO, offering an enjoyable challenge for casual players.

The project is inspired by Eddie Sharick, who has an excellent YouTube series detailing the process of building this game from scratch. While closely following his tutorials, I also introduced several enhancements and personal touches to the design and functionality.

I highly encourage you to visit Eddie Sharick's YouTube channel and explore his insightful series for yourself!

[Eddie's YouTube channel](https://www.youtube.com/channel/UCaEohRz5bPHywGBwmR18Qww)

## Project Structure
The project is organized into the following directories:

- `src/`: Contains all the source code files.
  - `ChessDriver.py`: The main driver file for the application.
  - `ChessEngine.py`: Contains classes for defining restricting and validating possible moves.
  - `ChessAI.py`: AI bot playing the game against the player, it involves different tactics such as Mobility, static position and dynamic positions to evaluate the best move.
- `assets/`: Contains all non-code assets.
  - `images/`: Contains all image files used in the project.
  - `sounds/`: Contains all sound files used in the project.
- `.gitignore`: Specifies files and directories to be ignored by git.
- `requirements.txt`: Lists the dependencies required for the project.

## Installation
To set up the project locally, follow these steps:

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/chess.git
    cd chess
    ```

2. Install the dependencies:
    ```sh
    pip install -r requirements.txt
    ```

## Usage

1. Select whether you want to play versus computer, against another player locally, or watch the game of engine playing against itself by setting appropriate flags in lines 58 and 59 of `src/ChessDriver.py`.

2. To run the application, execute the following command:
```sh
python src/ChessDriver.py
```
This will launch the game in a new window.


## Contributing
Contributions are welcome! Please follow these steps to contribute:

1. Fork the repository.
2. Create a new branch:
    ```sh
    git checkout -b feature-branch
    ```
3. Make your changes and commit them:
    ```sh
    git commit -m "Description of your changes"
    ```
4. Push to the branch:
    ```sh
    git push origin feature-branch
    ```
5. Create a pull request.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements
- Inspired by lichess.org and chess.com.
- AI chess bot "The Dragon" developed by following Eddie Sharick's YouTube channel.
