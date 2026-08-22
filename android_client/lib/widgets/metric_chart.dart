import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../theme/colors.dart';

class MetricChart extends StatelessWidget {
  final List<double> data;
  final Color color;
  final String? title;
  final double minY;
  final double? maxY;

  const MetricChart({
    super.key,
    required this.data,
    required this.color,
    this.title,
    this.minY = 0,
    this.maxY,
  });

  @override
  Widget build(BuildContext context) {
    if (data.length < 2) {
      return const Center(child: CircularProgressIndicator());
    }

    final spots = <FlSpot>[];
    for (int i = 0; i < data.length; i++) {
      spots.add(FlSpot(i.toDouble(), data[i]));
    }

    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: true, drawVerticalLine: false),
        titlesData: const FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        minY: minY,
        maxY: maxY,
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: color,
            barWidth: 2,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              color: color.withOpacity(0.1),
            ),
          ),
        ],
      ),
    );
  }
}
