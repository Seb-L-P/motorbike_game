import pickle
import neat
from neonride_ai import NeonRideAI

with open("best_bike_ai.pkl", "rb") as f:
    winner = pickle.load(f)

config = neat.Config(
    neat.DefaultGenome, neat.DefaultReproduction,
    neat.DefaultSpeciesSet, neat.DefaultStagnation,
    "config-feedforward.txt"
)

net = neat.nn.FeedForwardNetwork.create(winner, config)
env = NeonRideAI(render=True)
state = env.reset()

done = False
while not done:
    output = net.activate(state)
    action = output.index(max(output))
    state, _, done = env.step(action)
