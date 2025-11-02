import neat
import pickle
from neonride_ai import NeonRideAI

def eval_genome(genome, config):
    env = NeonRideAI(render=False)
    net = neat.nn.FeedForwardNetwork.create(genome, config)
    state = env.reset()
    fitness = 0
    while True:
        output = net.activate(state)
        action = output.index(max(output))  # 0=stay,1=left,2=right
        state, reward, done = env.step(action)
        fitness += reward
        if done:
            break
    return fitness

def eval_genomes(genomes, config):
    for genome_id, genome in genomes:
        genome.fitness = eval_genome(genome, config)

def run_neat(config_path):
    config = neat.Config(
        neat.DefaultGenome, neat.DefaultReproduction,
        neat.DefaultSpeciesSet, neat.DefaultStagnation, config_path
    )

    population = neat.Population(config)
    population.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    population.add_reporter(stats)

    winner = population.run(eval_genomes, 50)
    print("\n🏆 Winner genome:", winner)
    with open("best_bike_ai.pkl", "wb") as f:
        pickle.dump(winner, f)

if __name__ == "__main__":
    run_neat("config-feedforward.txt")
