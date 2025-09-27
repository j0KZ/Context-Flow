// Package contextflow provides high-performance compression with KB-scale memory footprint
package contextflow

import (
	"bytes"
	"encoding/binary"
	"errors"
	"fmt"
	"hash/crc32"
	"io"
	"math"
	"sync"
)

const (
	// Version information
	VersionMajor = 4
	VersionMinor = 0
	VersionPatch = 0
	Version      = "4.0.0"

	// Constants
	MinMatch    = 3
	MaxMatch    = 258
	WindowSize  = 32768
	HashSize    = 65536
	BlockSize   = 65536
	MaxContexts = 256
)

// CompressionLevel represents the compression level
type CompressionLevel int

const (
	Fastest CompressionLevel = 1
	Fast    CompressionLevel = 3
	Default CompressionLevel = 6
	Better  CompressionLevel = 7
	Best    CompressionLevel = 9
)

// Mode represents the compression mode
type Mode int

const (
	ModeStandard Mode = iota
	ModeTurbo
	ModeQuantum
	ModeStreaming
	ModeDelta
	ModeDictionary
)

// Error types
var (
	ErrInvalidInput        = errors.New("invalid input")
	ErrOutOfMemory         = errors.New("out of memory")
	ErrCompressionFailed   = errors.New("compression failed")
	ErrDecompressionFailed = errors.New("decompression failed")
	ErrInvalidFormat       = errors.New("invalid format")
	ErrChecksumMismatch    = errors.New("checksum mismatch")
	ErrUnsupportedMode     = errors.New("unsupported mode")
)

// Statistics holds compression statistics
type Statistics struct {
	OriginalSize        uint64
	CompressedSize      uint64
	CompressionRatio    float64
	CompressionSpeedMBs float64
	MemoryUsed          uint64
	Checksum            uint32
}

// lz77Match represents an LZ77 match
type lz77Match struct {
	distance uint16
	length   uint8
}

// contextModel represents a context model for prediction
type contextModel struct {
	counts [256]uint32
	total  uint32
}

// rangeEncoder represents a range encoder state
type rangeEncoder struct {
	low       uint64
	rangeVal  uint64
	buffer    *bytes.Buffer
	byteCount uint64
}

// Context represents a compression context
type Context struct {
	mode  Mode
	level CompressionLevel

	// LZ77 components
	window    []byte
	windowPos int
	hashTable []uint16
	hashChain []uint16

	// Context modeling
	contexts [4]*contextModel
	history  []byte

	// Statistics
	stats Statistics

	// Dictionary support
	dictionary []byte

	// Streaming state
	streaming     bool
	streamBuffer  []byte
	mu            sync.Mutex
}

// NewContext creates a new compression context
func NewContext(mode Mode, level CompressionLevel) (*Context, error) {
	ctx := &Context{
		mode:      mode,
		level:     level,
		window:    make([]byte, WindowSize),
		hashTable: make([]uint16, HashSize),
		hashChain: make([]uint16, WindowSize),
		history:   make([]byte, 256),
	}

	// Initialize hash tables with max value
	for i := range ctx.hashTable {
		ctx.hashTable[i] = 0xFFFF
	}
	for i := range ctx.hashChain {
		ctx.hashChain[i] = 0xFFFF
	}

	// Initialize context models
	for i := range ctx.contexts {
		ctx.contexts[i] = newContextModel()
	}

	return ctx, nil
}

// newContextModel creates a new context model
func newContextModel() *contextModel {
	model := &contextModel{}
	for i := range model.counts {
		model.counts[i] = 1 // Avoid zero probability
	}
	model.total = 256
	return model
}

// update updates the context model with a symbol
func (m *contextModel) update(symbol byte) {
	m.counts[symbol]++
	m.total++

	// Rescale if total gets too large
	if m.total > 65536 {
		m.total = 0
		for i := range m.counts {
			m.counts[i] = (m.counts[i] + 1) / 2
			m.total += m.counts[i]
		}
	}
}

// hash3 computes a 3-byte hash
func hash3(data []byte) uint32 {
	if len(data) < 3 {
		return 0
	}
	return (uint32(data[0])*31*31 + uint32(data[1])*31 + uint32(data[2])) & (HashSize - 1)
}

// findMatch finds the best LZ77 match
func (ctx *Context) findMatch(data []byte, pos int) lz77Match {
	best := lz77Match{0, 0}

	if pos+MinMatch > len(data) {
		return best
	}

	hash := hash3(data[pos:])
	chainPos := ctx.hashTable[hash]
	chainLength := int(ctx.level) * 16

	for chainPos != 0xFFFF && chainLength > 0 {
		chainLength--

		if int(chainPos) < ctx.windowPos {
			distance := ctx.windowPos - int(chainPos)

			if distance <= 32768 {
				// Compare bytes
				matchLen := 0
				maxLen := len(data) - pos
				if maxLen > MaxMatch {
					maxLen = MaxMatch
				}

				for matchLen < maxLen &&
					data[pos+matchLen] == ctx.window[int(chainPos)+matchLen] {
					matchLen++
				}

				if matchLen >= MinMatch && matchLen > int(best.length) {
					best.distance = uint16(distance)
					best.length = uint8(matchLen)

					if matchLen >= MaxMatch {
						break
					}
				}
			}
		}

		chainPos = ctx.hashChain[chainPos]
	}

	return best
}

// updateHash updates the hash tables
func (ctx *Context) updateHash(data []byte, pos int) {
	if pos+MinMatch <= len(data) {
		hash := hash3(data[pos:])
		ctx.hashChain[ctx.windowPos] = ctx.hashTable[hash]
		ctx.hashTable[hash] = uint16(ctx.windowPos)

		ctx.window[ctx.windowPos] = data[pos]
		ctx.windowPos = (ctx.windowPos + 1) % WindowSize
	}
}

// Compress compresses data
func Compress(data []byte, level CompressionLevel) ([]byte, error) {
	ctx, err := NewContext(ModeStandard, level)
	if err != nil {
		return nil, err
	}
	return ctx.Compress(data)
}

// Decompress decompresses data
func Decompress(data []byte) ([]byte, error) {
	ctx, err := NewContext(ModeStandard, Default)
	if err != nil {
		return nil, err
	}
	return ctx.Decompress(data)
}

// Compress compresses data using the context
func (ctx *Context) Compress(data []byte) ([]byte, error) {
	ctx.mu.Lock()
	defer ctx.mu.Unlock()

	if len(data) == 0 {
		return []byte{}, nil
	}

	var output bytes.Buffer

	// Write header
	output.WriteByte('C')
	output.WriteByte('T')
	output.WriteByte('X')
	output.WriteByte('F')
	output.WriteByte(byte(ctx.mode))
	output.WriteByte(byte(ctx.level))
	binary.Write(&output, binary.BigEndian, uint32(len(data)))

	// LZ77 compression for standard and turbo modes
	if ctx.mode == ModeStandard || ctx.mode == ModeTurbo {
		pos := 0

		for pos < len(data) {
			match := ctx.findMatch(data, pos)

			if match.length >= MinMatch {
				// Encode match
				output.WriteByte(0x80 | match.length)
				binary.Write(&output, binary.BigEndian, match.distance)

				// Update hash for matched bytes
				for i := 0; i < int(match.length); i++ {
					ctx.updateHash(data, pos+i)
				}
				pos += int(match.length)
			} else {
				// Encode literal
				output.WriteByte(data[pos])
				ctx.updateHash(data, pos)
				pos++
			}
		}
	} else {
		// Simple copy for other modes (placeholder)
		output.Write(data)
	}

	// Calculate checksum
	checksum := crc32.ChecksumIEEE(data)
	binary.Write(&output, binary.BigEndian, checksum)

	// Update statistics
	ctx.stats.OriginalSize = uint64(len(data))
	ctx.stats.CompressedSize = uint64(output.Len())
	ctx.stats.CompressionRatio = float64(len(data)) / float64(output.Len())
	ctx.stats.Checksum = checksum

	return output.Bytes(), nil
}

// Decompress decompresses data using the context
func (ctx *Context) Decompress(data []byte) ([]byte, error) {
	ctx.mu.Lock()
	defer ctx.mu.Unlock()

	if len(data) < 14 { // Header (10) + checksum (4)
		return nil, ErrInvalidFormat
	}

	reader := bytes.NewReader(data)

	// Read and verify header
	header := make([]byte, 4)
	reader.Read(header)
	if string(header) != "CTXF" {
		return nil, ErrInvalidFormat
	}

	var mode, level byte
	var originalSize uint32

	reader.ReadByte()         // mode
	reader.ReadByte()         // level
	binary.Read(reader, binary.BigEndian, &originalSize)

	output := make([]byte, 0, originalSize)

	// Decompress based on mode
	if mode == byte(ModeStandard) || mode == byte(ModeTurbo) {
		for reader.Len() > 4 { // Keep 4 bytes for checksum
			b, err := reader.ReadByte()
			if err != nil {
				break
			}

			if b&0x80 != 0 {
				// Match
				length := int(b & 0x7F)
				var distance uint16
				binary.Read(reader, binary.BigEndian, &distance)

				if len(output) < int(distance) {
					return nil, ErrInvalidFormat
				}

				// Copy match
				for i := 0; i < length; i++ {
					output = append(output, output[len(output)-int(distance)])
				}
			} else {
				// Literal
				output = append(output, b)
			}

			if len(output) >= int(originalSize) {
				break
			}
		}
	} else {
		// Simple copy for other modes
		remaining := reader.Len() - 4
		simpleCopy := make([]byte, remaining)
		reader.Read(simpleCopy)
		output = append(output, simpleCopy...)
	}

	// Verify checksum
	var storedChecksum uint32
	binary.Read(reader, binary.BigEndian, &storedChecksum)

	calculatedChecksum := crc32.ChecksumIEEE(output)
	if storedChecksum != calculatedChecksum {
		return nil, ErrChecksumMismatch
	}

	return output, nil
}

// Reset resets the context for reuse
func (ctx *Context) Reset() {
	ctx.mu.Lock()
	defer ctx.mu.Unlock()

	// Reset LZ77 state
	ctx.windowPos = 0
	for i := range ctx.hashTable {
		ctx.hashTable[i] = 0xFFFF
	}
	for i := range ctx.hashChain {
		ctx.hashChain[i] = 0xFFFF
	}

	// Reset context models
	for _, model := range ctx.contexts {
		for i := range model.counts {
			model.counts[i] = 1
		}
		model.total = 256
	}

	// Clear history
	for i := range ctx.history {
		ctx.history[i] = 0
	}

	// Clear statistics
	ctx.stats = Statistics{}
}

// Statistics returns compression statistics
func (ctx *Context) Statistics() Statistics {
	ctx.mu.Lock()
	defer ctx.mu.Unlock()
	return ctx.stats
}

// LoadDictionary loads a dictionary for compression
func (ctx *Context) LoadDictionary(dictionary []byte) {
	ctx.mu.Lock()
	defer ctx.mu.Unlock()
	ctx.dictionary = dictionary
}

// StreamCompressor provides streaming compression
type StreamCompressor struct {
	ctx    *Context
	buffer bytes.Buffer
}

// NewStreamCompressor creates a new stream compressor
func NewStreamCompressor(level CompressionLevel) (*StreamCompressor, error) {
	ctx, err := NewContext(ModeStreaming, level)
	if err != nil {
		return nil, err
	}

	return &StreamCompressor{
		ctx: ctx,
	}, nil
}

// Write implements io.Writer
func (s *StreamCompressor) Write(p []byte) (n int, err error) {
	s.buffer.Write(p)

	// Process in chunks
	for s.buffer.Len() >= BlockSize {
		chunk := make([]byte, BlockSize)
		s.buffer.Read(chunk)

		compressed, err := s.ctx.Compress(chunk)
		if err != nil {
			return 0, err
		}

		// In real implementation, would write to output
		_ = compressed
	}

	return len(p), nil
}

// Flush flushes any buffered data
func (s *StreamCompressor) Flush() error {
	if s.buffer.Len() > 0 {
		remaining := s.buffer.Bytes()
		compressed, err := s.ctx.Compress(remaining)
		if err != nil {
			return err
		}

		// In real implementation, would write to output
		_ = compressed
		s.buffer.Reset()
	}

	return nil
}

// Close closes the stream compressor
func (s *StreamCompressor) Close() error {
	return s.Flush()
}

// DictionaryBuilder builds compression dictionaries
type DictionaryBuilder struct {
	samples [][]byte
}

// NewDictionaryBuilder creates a new dictionary builder
func NewDictionaryBuilder() *DictionaryBuilder {
	return &DictionaryBuilder{
		samples: make([][]byte, 0),
	}
}

// AddSample adds a sample for dictionary training
func (b *DictionaryBuilder) AddSample(sample []byte) {
	b.samples = append(b.samples, sample)
}

// Build builds a dictionary from samples
func (b *DictionaryBuilder) Build(maxSize int) ([]byte, error) {
	if len(b.samples) == 0 {
		return nil, ErrInvalidInput
	}

	// Simple frequency analysis
	frequency := make(map[string]int)

	for _, sample := range b.samples {
		for i := 0; i < len(sample)-3; i++ {
			pattern := string(sample[i : i+4])
			frequency[pattern]++
		}
	}

	// Build dictionary from most frequent patterns
	dictionary := bytes.Buffer{}

	type pair struct {
		pattern string
		count   int
	}

	pairs := make([]pair, 0, len(frequency))
	for pattern, count := range frequency {
		pairs = append(pairs, pair{pattern, count})
	}

	// Sort by frequency (simple bubble sort for demo)
	for i := 0; i < len(pairs); i++ {
		for j := i + 1; j < len(pairs); j++ {
			if pairs[j].count > pairs[i].count {
				pairs[i], pairs[j] = pairs[j], pairs[i]
			}
		}
	}

	// Add patterns to dictionary
	for _, p := range pairs {
		if dictionary.Len()+len(p.pattern) > maxSize {
			break
		}
		dictionary.WriteString(p.pattern)
	}

	return dictionary.Bytes(), nil
}

// ComputeDelta computes delta between two versions
func ComputeDelta(base, target []byte) ([]byte, error) {
	var delta bytes.Buffer

	// Simple delta encoding (placeholder)
	// In real implementation, would use more sophisticated algorithm

	// Write header
	delta.WriteByte('D')
	delta.WriteByte('L')
	delta.WriteByte('T')
	delta.WriteByte('A')

	binary.Write(&delta, binary.BigEndian, uint32(len(base)))
	binary.Write(&delta, binary.BigEndian, uint32(len(target)))

	// Find common prefix
	commonPrefix := 0
	for commonPrefix < len(base) && commonPrefix < len(target) &&
		base[commonPrefix] == target[commonPrefix] {
		commonPrefix++
	}

	// Encode operations
	if commonPrefix > 0 {
		delta.WriteByte(0x01) // COPY operation
		binary.Write(&delta, binary.BigEndian, uint32(commonPrefix))
	}

	// Add remaining target bytes
	if commonPrefix < len(target) {
		delta.WriteByte(0x02) // ADD operation
		binary.Write(&delta, binary.BigEndian, uint32(len(target)-commonPrefix))
		delta.Write(target[commonPrefix:])
	}

	return delta.Bytes(), nil
}

// ApplyDelta applies delta to base version
func ApplyDelta(base, delta []byte) ([]byte, error) {
	if len(delta) < 12 {
		return nil, ErrInvalidFormat
	}

	reader := bytes.NewReader(delta)

	// Read header
	header := make([]byte, 4)
	reader.Read(header)
	if string(header) != "DLTA" {
		return nil, ErrInvalidFormat
	}

	var baseSize, targetSize uint32
	binary.Read(reader, binary.BigEndian, &baseSize)
	binary.Read(reader, binary.BigEndian, &targetSize)

	output := make([]byte, 0, targetSize)

	// Process operations
	for reader.Len() > 0 {
		op, err := reader.ReadByte()
		if err != nil {
			break
		}

		switch op {
		case 0x01: // COPY
			var length uint32
			binary.Read(reader, binary.BigEndian, &length)
			if int(length) <= len(base) {
				output = append(output, base[:length]...)
			}

		case 0x02: // ADD
			var length uint32
			binary.Read(reader, binary.BigEndian, &length)
			add := make([]byte, length)
			reader.Read(add)
			output = append(output, add...)

		default:
			return nil, ErrInvalidFormat
		}
	}

	return output, nil
}

// CompressFile compresses a file
func CompressFile(inputPath, outputPath string, level CompressionLevel) error {
	// In real implementation, would read/write files
	// This is a placeholder
	return fmt.Errorf("file compression not implemented")
}

// DecompressFile decompresses a file
func DecompressFile(inputPath, outputPath string) error {
	// In real implementation, would read/write files
	// This is a placeholder
	return fmt.Errorf("file decompression not implemented")
}