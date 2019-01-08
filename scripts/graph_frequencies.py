import argparse, sys, os, glob, json
import numpy as np
import matplotlib
# important to use a non-interactive backend, otherwise will crash on cluster
matplotlib.use('agg')
import matplotlib.pyplot as plt
from matplotlib.dates import YearLocator, MonthLocator, DateFormatter

cols = [ '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2',
         '#7f7f7f', '#bcbd22', '#17becf']
region_label = {'global': 'Global', #'NA': 'N America', 'AS': 'Asia', 'EU': 'Europe', 'OC': 'Oceania',
                'north_america': 'N America', 'asia': 'Asia', 'europe': 'Europe', 'oceania': 'Oceania',
                'south_asia': 'S Asia', 'southeast_asia':"SE Asia", 'west_asia':'W Asia', 'south_america':'S America',
                'japan_korea':"Japan/Korea", "china":"China", "africa":"Africa"}

region_colors = {r:cols[ri%len(cols)] for ri,r in enumerate(sorted(region_label.keys()))}

fs=12
ymax=800
years = YearLocator()
months = MonthLocator(range(1, 13), bymonthday=1, interval=2)
yearsFmt = DateFormatter('%Y')
monthsFmt = DateFormatter("%b")


def load_frequencies(fname):
    with open(fname) as fh:
        return json.load(fh)


def plot_mutations_by_region(frequencies, mutations, fname,show_errorbars=True,
                             n_std_dev=1, n_smooth=3, drop=3):
    regions = sorted(frequencies.keys())
    smoothed_count_by_region = {}
    # generate a temporally smoothed sample count vector for each region.
    for region, freqs in frequencies.items():
        for n, f in freqs.items():
            if 'count' in n:
                gene = n.split(':')[0]
                smoothed_count_by_region[(gene, region)] = np.convolve(np.ones(n_smooth, dtype=float)/n_smooth, f, mode='same')

    # set up a figure and plot each mutation in a different panel
    fig, axs = plt.subplots(len(mutations), 1, sharex=True, figsize=(8,1+2*len(mutations)))
    for mi,(mut, ax) in enumerate(zip(mutations, axs)):
        gene = mut.split(':')[0]
        for region in regions:
            pivots = frequencies[region]["pivots"]
            if mut in frequencies[region]:
                tmp_freq = np.array(frequencies[region][mut])
                ax.plot(pivots[:-drop], tmp_freq[:-drop], '-o', lw=4 if region=='global' else 2,
                        label=region_label.get(region, region), c=region_colors[region])
                std_dev = np.sqrt(tmp_freq*(1-tmp_freq)/(smoothed_count_by_region[(gene, region)]+1))
                if show_errorbars:
                    ax.fill_between(pivots[:-drop], (tmp_freq-n_std_dev*std_dev)[:-drop],
                                    (tmp_freq+n_std_dev*std_dev)[:-drop],
                                    facecolor=region_colors[region], linewidth=0, alpha=0.1)
            else:
                print("Mutation %s not calculated in region %s"%(mut, region))
            if mi==0:
                ax.legend(ncol=2)
            if mi==len(mutations)-1:
                ax.set_xlabel('time', fontsize=fs)
            ax.set_ylabel(mut, fontsize=fs)
            ax.set_ylim(0,1)

    plt.subplots_adjust(hspace=0)
    plt.tight_layout()
    plt.savefig(fname)


def plot_clades_by_region(frequencies, clades, clade_to_node, fname,show_errorbars=True,
                          n_std_dev=1, n_smooth=3, drop=3):
    smoothed_count_by_region = {}
    total_count_by_region = {}
    for region in frequencies['counts']:
        smoothed_count_by_region[region] = np.convolve(np.ones(n_smooth, dtype=float)/n_smooth,
                                                       frequencies['counts'][region], mode='same')
        total_count_by_region[region] = np.sum(frequencies['counts'][region])

    regions = ['north_america', 'china', 'japan_korea', 'oceania', 'europe', 'southeast_asia']

    fig, axs = plt.subplots(len(clades), 1, sharex=True, figsize=(8,1+2*len(clades)))
    for mi,(clade, ax) in enumerate(zip(clades, axs)):
        if clade not in clade_to_node:
            print("Clade %s is not annotated"%clade)
            continue

        node = clade_to_node[clade]
        for region in regions:
            pivots = frequencies["pivots"]
            if node in frequencies and region in frequencies[node]:
                tmp_freq = np.array(frequencies[node][region])
                ax.plot(pivots[:-drop], tmp_freq[:-drop], '-o', lw=4 if region=='global' else 2,
                        label=region_label.get(region, region), c=region_colors[region])
                std_dev = np.sqrt(tmp_freq*(1-tmp_freq)/(smoothed_count_by_region[region]+1))
                if show_errorbars:
                    ax.fill_between(pivots[:-drop], (tmp_freq-n_std_dev*std_dev)[:-drop],
                                    (tmp_freq+n_std_dev*std_dev)[:-drop],
                                    facecolor=region_colors[region], linewidth=0, alpha=0.1)
            else:
                print("region %s not present in node %s"%(region, node))
            if mi==0:
                ax.legend(ncol=2)
            if mi==len(clades)-1:
                ax.set_xlabel('time', fontsize=fs)
            ax.set_ylabel(clade, fontsize=fs)
            ax.set_ylim(0,1)

    plt.subplots_adjust(hspace=0)
    plt.tight_layout()
    plt.savefig(fname)


def sample_count_by_region(frequencies, fname):
    regions = sorted(frequencies.keys())
    counts = {}
    for region in frequencies:
        date_bins = frequencies[region]["pivots"]
        tmp = [frequencies[region][x] for x in frequencies[region] if 'counts' in x]
        if len(tmp):
            counts[region] = tmp[0]

    if 'global' not in counts:
        if len(counts)>1:
            counts["global"] = np.sum([x for x in counts.values()], axis=0)
        else:
            counts["global"] = list(counts.values())[0]
    plot_counts(counts, date_bins, fname, drop=3)


def tree_sample_counts(tree_frequencies, fname):
    date_bins = tree_frequencies["pivots"]
    counts = tree_frequencies["counts"]
    if 'global' not in counts:
        counts["global"] = np.sum([x for x in counts.values()], axis=1)

    plot_counts(counts, date_bins, fname, drop=3)


def plot_counts(counts, date_bins, fname, drop=3):
    fig, ax = plt.subplots(figsize=(8, 3))
    regions = sorted(counts.keys())
    tmpcounts = np.zeros(len(date_bins))
    width = 0.9*(date_bins[1] - date_bins[0])
    plt.bar(date_bins, counts['global'], width=width, linewidth=0,
            label="Other", color="#bbbbbb", clip_on=False)

    for region in regions:
        if region!='global':
            plt.bar(date_bins, counts[region], bottom=tmpcounts, width=width, linewidth=0,
                    label=region_label.get(region, region), color=region_colors[region],
                    clip_on=False, alpha=0.8)
            tmpcounts += np.array(counts[region])
    ax.set_xlim([date_bins[0]-width*0.5, date_bins[-1]])
    ax.set_ylim(0,min(max(counts['global']), ymax))
    ax.tick_params(axis='x', which='major', labelsize=fs, pad=20)
    ax.tick_params(axis='x', which='minor', pad=7)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.set_ylabel('Sample count', fontsize=fs*1.1)
    ax.legend(loc=2, ncol=2)
    plt.subplots_adjust(left=0.1, right=0.82, top=0.94, bottom=0.22)
    if fname:
        plt.savefig(fname)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Separate strains by region and align specific genes",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument('--mutation-frequencies', nargs='+',
                        help="json files containing frequencies in different regions")
    parser.add_argument('--tree-frequencies', type=str,
                        help="json files containing frequencies of clades in the tree")
    parser.add_argument('--clade-annotations', type=str,
                        help="json files containing clade annotations to map internal nodes to clades")
    parser.add_argument('--mutations',nargs='+', help="mutations to graph")
    parser.add_argument('--clades',nargs='+', help="clades to graph")
    parser.add_argument('--regions',nargs='+', required=True, help="regions corresponding to alignment files")
    parser.add_argument('--output-mutations', help="file name to save figure to")
    parser.add_argument('--output-total-counts', help="file name to save figure to")
    parser.add_argument('--output-tree-counts', help="file name to save figure to")
    parser.add_argument('--output-clades', help="file name to save figure to")

    args=parser.parse_args()

    if args.mutation_frequencies:
        frequencies = {}
        for region, fname in zip(args.regions, args.mutation_frequencies):
            frequencies[region] = load_frequencies(fname)
        plot_mutations_by_region(frequencies, args.mutations, args.output_mutations)
        sample_count_by_region(frequencies, args.output_total_counts)


    if args.tree_frequencies:
        tree_frequencies = load_frequencies(args.tree_frequencies)
        tree_sample_counts(tree_frequencies, args.output_tree_counts)

        if args.clade_annotations:
            clade_annotations = load_frequencies(args.clade_annotations)
            clade_to_node = {node["clade_annotation"]:node_name for node_name, node in clade_annotations['nodes'].items()
                             if "clade_annotation" in node}

            plot_clades_by_region(tree_frequencies, args.clades, clade_to_node, args.output_clades)
